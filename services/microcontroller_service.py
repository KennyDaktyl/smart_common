import logging
from typing import Any, Callable, Optional
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from smart_common.core import db
from smart_common.enums.event import EventType
from smart_common.models.microcontroller import Microcontroller
from smart_common.models.microcontroller_sensor_capability import (
    MicrocontrollerSensorCapability,
)
from smart_common.enums.sensor import SensorType
from smart_common.events.device_events import MicrocontrollerCommandPayload
from smart_common.events.event_dispatcher import EventDispatcher
from smart_common.nats.client import NATSClient
from smart_common.nats.event_helpers import (
    ack_subject_for_entity,
    subject_for_entity,
    stream_name,
)
from smart_common.nats.publisher import NatsPublisher
from smart_common.providers.enums import ProviderKind, ProviderType
from smart_common.providers.registry import resolve_sensor_type
from smart_common.repositories.microcontroller import MicrocontrollerRepository
from smart_common.repositories.provider import ProviderRepository
from smart_common.schemas.automation_rule import (
    AutomationRuleGroup,
    AutomationRuleSource,
    build_legacy_power_rule,
    uses_source,
)
from smart_common.schemas.microcontroller_schema import (
    MicrocontrollerAgentCommand,
    MicrocontrollerAgentConfigFilesUpdateRequest,
    MicrocontrollerAgentCommandAck,
    MicrocontrollerConfigUpdateRequest,
)


class MicrocontrollerService:

    def __init__(
        self,
        repo_factory: Callable[[Session], MicrocontrollerRepository],
        provider_repo_factory: Optional[Callable[[Session], ProviderRepository]] = None,
    ):
        self._repo_factory = repo_factory
        self._provider_repo_factory = provider_repo_factory
        self.logger = logging.getLogger(__name__)
        self.events = EventDispatcher(NatsPublisher(NATSClient()))

    def _repo(self, db: Session) -> MicrocontrollerRepository:
        return self._repo_factory(db)

    def _provider_repo(self, db: Session) -> ProviderRepository:
        if not self._provider_repo_factory:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Provider repository is not configured",
            )
        return self._provider_repo_factory(db)

    @staticmethod
    def _provider_config_payload(provider) -> dict[str, Any] | None:
        if provider is None:
            return None

        return {
            "uuid": str(provider.uuid),
            "external_id": provider.external_id or "",
            "unit": provider.unit.value if getattr(provider, "unit", None) is not None else None,
            "has_power_meter": bool(getattr(provider, "has_power_meter", False)),
            "has_energy_storage": bool(getattr(provider, "has_energy_storage", False)),
        }

    @staticmethod
    def _rule_uses_battery_source(rule_data) -> bool:
        if rule_data is None:
            return False
        if isinstance(rule_data, dict):
            try:
                rule_data = AutomationRuleGroup.model_validate(rule_data)
            except Exception:
                return False
        return uses_source(
            rule_data,
            AutomationRuleSource.PROVIDER_BATTERY_SOC,
        )

    @classmethod
    def _device_uses_battery_rule(cls, device, provider_unit: str | None) -> bool:
        rule_data = getattr(device, "auto_rule_json", None)
        if rule_data is None and getattr(device, "threshold_value", None) is not None:
            rule_data = build_legacy_power_rule(
                value=float(device.threshold_value),
                unit=provider_unit or "W",
            )
        if cls._rule_uses_battery_source(rule_data):
            return True

        scheduler = getattr(device, "scheduler", None)
        for slot in getattr(scheduler, "slots", []) or []:
            if cls._rule_uses_battery_source(getattr(slot, "activation_rule_json", None)):
                return True

        return False

    def _ensure_provider_supports_existing_device_rules(
        self,
        *,
        microcontroller: Microcontroller,
        provider,
    ) -> None:
        if provider is None:
            return

        provider_unit = provider.unit.value if getattr(provider, "unit", None) is not None else None
        if bool(getattr(provider, "has_energy_storage", False)):
            return

        for device in getattr(microcontroller, "devices", []) or []:
            if self._device_uses_battery_rule(device, provider_unit):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        "Selected provider does not support battery state-of-charge "
                        "rules required by existing AUTO or scheduler devices"
                    ),
                )

    def _normalize_and_validate_sensors(
        self,
        sensors: list[str | SensorType],
    ) -> list[str]:
        normalized = self._normalize_sensor_values(sensors)

        if len(set(normalized)) != len(normalized):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="assigned_sensors must not contain duplicates",
            )

        return normalized

    def _apply_assigned_sensors(
        self,
        db: Session,
        *,
        microcontroller: Microcontroller,
        assigned_sensors: list[str],
    ) -> None:
        microcontroller.sensor_capabilities.clear()
        db.flush()
        microcontroller.sensor_capabilities.extend(
            MicrocontrollerSensorCapability(sensor_type=s)
            for s in assigned_sensors
        )

    def _sync_microcontroller_config(self, microcontroller: Microcontroller) -> None:
        config = dict(microcontroller.config or {})

        config["uuid"] = str(microcontroller.uuid)
        config["device_max"] = microcontroller.max_devices
        config["available_sensors"] = list(microcontroller.assigned_sensors)
        config.pop("device_uuid", None)
        config.setdefault("active_low", False)
        config.setdefault("devices_config", [])
        config.setdefault("provider", None)

        microcontroller.config = config

    def _register_microcontroller(
        self,
        db: Session,
        *,
        payload: dict[str, Any],
    ) -> Microcontroller:
        assigned_sensors = self._normalize_and_validate_sensors(
            payload.pop("assigned_sensors", []) or []
        )

        microcontroller = Microcontroller(
            **payload,
            sensor_capabilities=[
                MicrocontrollerSensorCapability(sensor_type=s) for s in assigned_sensors
            ],
            config={},
        )

        db.add(microcontroller)
        db.flush()
        self._sync_microcontroller_config(microcontroller)
        db.commit()
        db.refresh(microcontroller)

        return microcontroller

    def register_microcontroller_admin(
        self,
        db: Session,
        *,
        payload: dict,
    ) -> Microcontroller:
        return self._register_microcontroller(db, payload=payload)

    def register_microcontroller_for_user(
        self,
        db: Session,
        *,
        user_id: int,
        payload: dict[str, Any],
    ) -> Microcontroller:
        payload["user_id"] = user_id
        return self._register_microcontroller(db, payload=payload)

    def _update_microcontroller(
        self,
        db: Session,
        *,
        microcontroller: Microcontroller,
        data: dict[str, Any],
        assigned_sensors: list[str | SensorType] | None,
        allowed_fields: set[str],
        log_message: str,
    ) -> Microcontroller:
        for field, value in data.items():
            if field in allowed_fields:
                setattr(microcontroller, field, value)

        if assigned_sensors is not None:
            normalized = self._normalize_and_validate_sensors(assigned_sensors)
            self._apply_assigned_sensors(
                db,
                microcontroller=microcontroller,
                assigned_sensors=normalized,
            )

        self._sync_microcontroller_config(microcontroller)

        db.commit()
        db.refresh(microcontroller)

        self.logger.info(
            log_message,
            extra={
                "microcontroller_id": microcontroller.id,
                "fields": list(data.keys()),
                "assigned_sensors": assigned_sensors,
            },
        )

        return microcontroller

    def update_microcontroller_admin(
        self,
        db: Session,
        *,
        microcontroller_id: int,
        data: dict[str, Any],
        assigned_sensors: list[str | SensorType] | None,
    ) -> Microcontroller:
        repo = self._repo(db)

        microcontroller = repo.get_by_id(microcontroller_id)
        if not microcontroller:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Microcontroller not found",
            )

        return self._update_microcontroller(
            db,
            microcontroller=microcontroller,
            data=data,
            assigned_sensors=assigned_sensors,
            allowed_fields=repo.ADMIN_UPDATE_FIELDS,
            log_message="Microcontroller updated by admin",
        )

    def update_microcontroller_for_user(
        self,
        db: Session,
        *,
        microcontroller_uuid: UUID,
        user_id: int,
        data: dict[str, Any],
        assigned_sensors: list[str | SensorType] | None,
    ) -> Microcontroller:
        repo = self._repo(db)

        microcontroller = repo.get_for_user_by_uuid(
            uuid=microcontroller_uuid,
            user_id=user_id,
        )
        if not microcontroller:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Microcontroller not found",
            )

        return self._update_microcontroller(
            db,
            microcontroller=microcontroller,
            data=data,
            assigned_sensors=assigned_sensors,
            allowed_fields=repo.USER_UPDATE_FIELDS,
            log_message="Microcontroller updated by user",
        )

    def _normalize_sensor_values(self, sensors: list[str | SensorType]) -> list[str]:
        return [
            sensor.value if isinstance(sensor, SensorType) else str(sensor)
            for sensor in sensors
        ]

    def _jsonify(self, value: Any) -> Any:
        """
        Convert non-JSON-safe objects (UUID, Enum, datetime)
        into JSON-serializable primitives.
        """
        if isinstance(value, UUID):
            return str(value)

        if isinstance(value, list):
            return [self._jsonify(v) for v in value]

        if isinstance(value, dict):
            return {k: self._jsonify(v) for k, v in value.items()}

        return value

    def update_microcontroller_config(
        self,
        db: Session,
        *,
        microcontroller_id: int,
        payload: MicrocontrollerConfigUpdateRequest,
    ) -> Microcontroller:
        repo = self._repo(db)

        mc = repo.get_by_id(microcontroller_id)
        if not mc:
            raise HTTPException(status_code=404, detail="Microcontroller not found")

        config = mc.config or {}

        update_data = payload.model_dump(
            exclude_unset=True,
            mode="json",
        )

        update_data.pop("uuid", None)
        update_data.pop("device_max", None)
        update_data.pop("device_uuid", None)

        config.update(update_data)
        config.pop("device_uuid", None)
        mc.config = config

        db.commit()
        db.refresh(mc)
        return mc

    def _ack_command_id(self, event: dict) -> str | None:
        if not isinstance(event, dict):
            return None
        data = event.get("data")
        if not isinstance(data, dict):
            return None
        command_id = data.get("command_id")
        if isinstance(command_id, str):
            normalized = command_id.strip()
            return normalized or None
        return None

    async def _publish_microcontroller_command(
        self,
        *,
        microcontroller_uuid: UUID,
        payload: MicrocontrollerCommandPayload,
    ) -> dict[str, Any]:
        subject = subject_for_entity(
            microcontroller_uuid,
            EventType.MICROCONTROLLER_COMMAND.value,
        )
        ack_subject = ack_subject_for_entity(
            microcontroller_uuid,
            EventType.MICROCONTROLLER_COMMAND.value,
        )

        self.logger.info(
            "Publish microcontroller command | mc_uuid=%s subject=%s ack_subject=%s command=%s",
            microcontroller_uuid,
            subject,
            ack_subject,
            payload.command,
        )

        try:
            result = await self.events.publish_event_and_wait_for_ack(
                entity_type=EventType.MICROCONTROLLER_COMMAND.value,
                entity_id=str(microcontroller_uuid),
                event_type=EventType.MICROCONTROLLER_COMMAND,
                data=payload,
                predicate=lambda e: self._ack_command_id(e) == payload.command_id,
                timeout=15.0,
                subject=subject,
                ack_subject=ack_subject,
            )
        except Exception as exc:
            self.logger.error(
                "Microcontroller command ACK failed | mc_uuid=%s command=%s error=%s",
                microcontroller_uuid,
                payload.command,
                exc,
                exc_info=True,
            )
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail=f"Microcontroller did not acknowledge command {payload.command}: {exc}",
            ) from exc

        ack_data = result.get("data") if isinstance(result, dict) else None
        if not isinstance(ack_data, dict):
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Invalid microcontroller ACK payload",
            )

        if not ack_data.get("ok", False):
            detail = ack_data.get("message")
            message = detail if isinstance(detail, str) and detail else "Agent rejected command"
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=message,
            )

        return ack_data

    async def get_agent_config_files(
        self,
        db: Session,
        *,
        microcontroller_id: int,
    ) -> dict[str, Any]:
        mc = self._repo(db).get_by_id(microcontroller_id)
        if not mc:
            raise HTTPException(status_code=404, detail="Microcontroller not found")

        command_id = uuid4().hex
        ack_data = await self._publish_microcontroller_command(
            microcontroller_uuid=mc.uuid,
            payload=MicrocontrollerCommandPayload(
                command_id=command_id,
                command=MicrocontrollerAgentCommand.READ_CONFIG_FILES.value,
            ),
        )

        config_json = ack_data.get("config_json")
        hardware_config_json = ack_data.get("hardware_config_json")
        env_file_content = ack_data.get("env_file_content")

        if not isinstance(config_json, dict) or not isinstance(hardware_config_json, dict):
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Agent returned invalid config files payload",
            )
        if not isinstance(env_file_content, str):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Agent version does not support .env management yet",
            )

        return {
            "ok": True,
            "command_id": str(ack_data.get("command_id") or command_id),
            "command": MicrocontrollerAgentCommand.READ_CONFIG_FILES,
            "message": ack_data.get("message"),
            "config_json": config_json,
            "hardware_config_json": hardware_config_json,
            "env_file_content": env_file_content,
        }

    async def update_agent_config_files(
        self,
        db: Session,
        *,
        microcontroller_id: int,
        payload: MicrocontrollerAgentConfigFilesUpdateRequest,
    ) -> MicrocontrollerAgentCommandAck:
        mc = self._repo(db).get_by_id(microcontroller_id)
        if not mc:
            raise HTTPException(status_code=404, detail="Microcontroller not found")

        command_id = uuid4().hex
        ack_data = await self._publish_microcontroller_command(
            microcontroller_uuid=mc.uuid,
            payload=MicrocontrollerCommandPayload(
                command_id=command_id,
                command=MicrocontrollerAgentCommand.WRITE_CONFIG_FILES.value,
                config_json=payload.config_json,
                hardware_config_json=payload.hardware_config_json,
                env_file_content=payload.env_file_content,
            ),
        )

        return MicrocontrollerAgentCommandAck(
            ok=True,
            command_id=str(ack_data.get("command_id") or command_id),
            command=MicrocontrollerAgentCommand.WRITE_CONFIG_FILES,
            message=ack_data.get("message"),
        )

    async def reboot_agent(
        self,
        db: Session,
        *,
        microcontroller_id: int,
    ) -> MicrocontrollerAgentCommandAck:
        mc = self._repo(db).get_by_id(microcontroller_id)
        if not mc:
            raise HTTPException(status_code=404, detail="Microcontroller not found")

        command_id = uuid4().hex
        ack_data = await self._publish_microcontroller_command(
            microcontroller_uuid=mc.uuid,
            payload=MicrocontrollerCommandPayload(
                command_id=command_id,
                command=MicrocontrollerAgentCommand.REBOOT_AGENT.value,
            ),
        )

        return MicrocontrollerAgentCommandAck(
            ok=True,
            command_id=str(ack_data.get("command_id") or command_id),
            command=MicrocontrollerAgentCommand.REBOOT_AGENT,
            message=ack_data.get("message"),
        )

    async def update_agent(
        self,
        db: Session,
        *,
        microcontroller_id: int,
    ) -> MicrocontrollerAgentCommandAck:
        mc = self._repo(db).get_by_id(microcontroller_id)
        if not mc:
            raise HTTPException(status_code=404, detail="Microcontroller not found")

        command_id = uuid4().hex
        ack_data = await self._publish_microcontroller_command(
            microcontroller_uuid=mc.uuid,
            payload=MicrocontrollerCommandPayload(
                command_id=command_id,
                command=MicrocontrollerAgentCommand.UPDATE_AGENT.value,
            ),
        )

        return MicrocontrollerAgentCommandAck(
            ok=True,
            command_id=str(ack_data.get("command_id") or command_id),
            command=MicrocontrollerAgentCommand.UPDATE_AGENT,
            message=ack_data.get("message"),
        )

    async def set_power_provider(
        self,
        db: Session,
        *,
        user_id: int,
        microcontroller_uuid: UUID,
        provider_uuid: UUID | None,
    ) -> Microcontroller:
        microcontroller = self._repo(db).get_for_user_by_uuid(microcontroller_uuid, user_id)
        if not microcontroller:
            raise HTTPException(status_code=404, detail="Microcontroller not found")

        previous_provider_uuid = (
            str(microcontroller.power_provider.uuid)
            if getattr(microcontroller, "power_provider", None)
            else None
        )
        previous_provider_unit = (
            microcontroller.power_provider.unit.value
            if getattr(microcontroller, "power_provider", None)
            and getattr(microcontroller.power_provider, "unit", None) is not None
            else None
        )

        next_provider_id: int | None = None
        next_provider_uuid = str(provider_uuid) if provider_uuid is not None else None
        next_provider_unit: str | None = None
        next_provider_has_power_meter = False
        next_provider_has_energy_storage = False
        next_provider_config: dict[str, Any] | None = None

        if provider_uuid is not None:
            provider = self._provider_repo(db).get_for_user_by_uuid(provider_uuid, user_id)
            if not provider or not provider.enabled:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Provider not found or not available",
                )
            self._ensure_provider_supports_existing_device_rules(
                microcontroller=microcontroller,
                provider=provider,
            )
            next_provider_id = provider.id
            next_provider_uuid = str(provider.uuid)
            next_provider_unit = provider.unit.value if provider.unit is not None else None
            next_provider_has_power_meter = bool(provider.has_power_meter)
            next_provider_has_energy_storage = bool(provider.has_energy_storage)
            next_provider_config = self._provider_config_payload(provider)

        if (
            previous_provider_uuid == next_provider_uuid
            and previous_provider_unit == next_provider_unit
        ):
            self.logger.info(
                "Provider already set for microcontroller",
                extra={
                    "microcontroller_uuid": str(microcontroller.uuid),
                    "provider_uuid": next_provider_uuid,
                    "unit": next_provider_unit,
                },
            )
            return microcontroller

        ack_data = await self._publish_provider_updated(
            microcontroller_uuid=str(microcontroller.uuid),
            provider_uuid=next_provider_uuid,
            previous_provider_uuid=previous_provider_uuid,
            unit=next_provider_unit,
            has_power_meter=next_provider_has_power_meter,
            has_energy_storage=next_provider_has_energy_storage,
        )

        microcontroller.power_provider_id = next_provider_id
        config = dict(microcontroller.config or {})
        config["provider"] = next_provider_config
        microcontroller.config = config
        db.commit()
        db.refresh(microcontroller)

        self.logger.info(
            "Provider updated for microcontroller",
            extra={
                "microcontroller_uuid": str(microcontroller.uuid),
                "previous_provider_uuid": previous_provider_uuid,
                "provider_uuid": next_provider_uuid,
                "previous_unit": previous_provider_unit,
                "unit": next_provider_unit,
                "has_power_meter": next_provider_has_power_meter,
                "has_energy_storage": next_provider_has_energy_storage,
                "ack_changed": ack_data.get("changed"),
            },
        )

        return microcontroller

    async def _publish_provider_updated(
        self,
        *,
        microcontroller_uuid: str,
        provider_uuid: str | None,
        previous_provider_uuid: str | None,
        unit: str | None,
        has_power_meter: bool,
        has_energy_storage: bool,
    ) -> dict:
        event_type = EventType.PROVIDER_UPDATED
        subject = f"{stream_name()}.{microcontroller_uuid}.command.provider_updated"
        ack_subject = f"{stream_name()}.provider_update.ack"
        try:
            result = await self.events.publish_event_and_wait_for_ack(
                entity_type="microcontroller",
                entity_id=microcontroller_uuid,
                event_type=event_type,
                data={
                    "provider_uuid": provider_uuid,
                    "unit": unit,
                    "has_power_meter": has_power_meter,
                    "has_energy_storage": has_energy_storage,
                },
                predicate=lambda payload: self._provider_updated_ack_matches(
                    payload=payload,
                    microcontroller_uuid=microcontroller_uuid,
                    provider_uuid=provider_uuid,
                    unit=unit,
                    has_power_meter=has_power_meter,
                    has_energy_storage=has_energy_storage,
                ),
                timeout=10.0,
                subject=subject,
                ack_subject=ack_subject,
                source="backend",
            )
        except Exception as exc:
            self.logger.error(
                "PROVIDER_UPDATED ACK FAILED | mc_uuid=%s error=%s",
                microcontroller_uuid,
                exc,
                exc_info=True,
            )
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail=f"Microcontroller did not acknowledge PROVIDER_UPDATED event: {exc}",
            ) from exc

        ack_data = result.get("data") or {}
        if not ack_data.get("ok", False):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Agent rejected provider update",
            )

        changed = ack_data.get("changed")
        if changed not in {True, False}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Agent returned invalid provider update acknowledgement",
            )

        if str(ack_data.get("microcontroller_uuid")) != microcontroller_uuid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Agent ACK microcontroller_uuid mismatch",
            )

        expected_provider_uuid = provider_uuid
        got_provider_uuid = ack_data.get("provider_uuid")
        if expected_provider_uuid is None:
            if got_provider_uuid is not None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Agent ACK provider_uuid mismatch",
                )
        elif str(got_provider_uuid) != expected_provider_uuid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Agent ACK provider_uuid mismatch",
            )

        if changed is True:
            got_previous = ack_data.get("previous_provider_uuid")
            if previous_provider_uuid is None:
                if got_previous is not None:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Agent ACK previous_provider_uuid mismatch",
                    )
            elif str(got_previous) != previous_provider_uuid:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Agent ACK previous_provider_uuid mismatch",
                )

        if changed is False:
            self.logger.info(
                "Agent provider update was idempotent | mc_uuid=%s provider_uuid=%s",
                microcontroller_uuid,
                provider_uuid,
            )

        return ack_data

    def _provider_updated_ack_matches(
        self,
        *,
        payload: dict,
        microcontroller_uuid: str,
        provider_uuid: str | None,
        unit: str | None,
        has_power_meter: bool,
        has_energy_storage: bool,
    ) -> bool:
        if not isinstance(payload, dict):
            return False

        data = payload.get("data")
        if not isinstance(data, dict):
            return False

        if str(data.get("microcontroller_uuid")) != microcontroller_uuid:
            return False

        incoming_provider_uuid = data.get("provider_uuid")
        if provider_uuid is None:
            if incoming_provider_uuid is not None:
                return False
        elif str(incoming_provider_uuid) != provider_uuid:
            return False

        incoming_unit = data.get("unit")
        if unit is None:
            if incoming_unit is not None:
                return False
        elif str(incoming_unit) != unit:
            return False

        if bool(data.get("has_power_meter", False)) != has_power_meter:
            return False
        if bool(data.get("has_energy_storage", False)) != has_energy_storage:
            return False
        return True

    # def __init__(
    #     self,
    #     repo_factory: Callable[[Session], MicrocontrollerRepository],
    #     provider_repo_factory: Optional[Callable[[Session], ProviderRepository]] = None,
    # ):
    #     self._repo_factory = repo_factory
    #     self._provider_repo_factory = provider_repo_factory
    #     self.logger = logging.getLogger(__name__)

    # def _provider_repo(self, db: Session) -> ProviderRepository:
    #     if not self._provider_repo_factory:
    #         raise HTTPException(
    #             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    #             detail="Provider repository is not configured",
    #         )
    #     return self._provider_repo_factory(db)

    # def _ensure_microcontroller(self, db: Session, user_id: int, mc_uuid: UUID) -> Microcontroller:
    #     microcontroller = self._repo(db).get_for_user_by_uuid(mc_uuid, user_id)
    #     if not microcontroller:
    #         raise HTTPException(
    #             status_code=status.HTTP_404_NOT_FOUND,
    #             detail="Microcontroller not found",
    #         )
    #     return microcontroller

    # def list_for_user(self, db: Session, user_id: int) -> list[Microcontroller]:
    #     # Ensure related providers/sensors are loaded for UI summaries.
    #     return self._repo(db).get_full_for_user(user_id)

    # def update(self, db: Session, user_id: int, uuid: UUID, payload: dict) -> Microcontroller:
    #     microcontroller = self._repo(db).update_for_user(uuid, user_id, payload)
    #     if not microcontroller:
    #         raise HTTPException(
    #             status_code=status.HTTP_404_NOT_FOUND,
    #             detail="Microcontroller not found or does not belong to user",
    #         )
    #     db.commit()
    #     db.refresh(microcontroller)
    #     self.logger.info(
    #         "Microcontroller updated",
    #         extra={
    #             "user_id": user_id,
    #             "microcontroller_uuid": microcontroller.uuid,
    #             "fields": list(payload.keys()),
    #         },
    #     )
    #     return microcontroller

    # def get_owned(self, db: Session, user_id: int, mc_uuid: UUID) -> Microcontroller:
    #     return self._ensure_microcontroller(db, user_id, mc_uuid)

    # def set_enabled(self, db: Session, user_id: int, uuid: UUID, enabled: bool) -> Microcontroller:
    #     return self.update(db, user_id, uuid, {"enabled": enabled})

    # def set_power_provider(
    #     self,
    #     db: Session,
    #     user_id: int,
    #     mc_uuid: UUID,
    #     provider_uuid: UUID | None,
    # ) -> Microcontroller:
    #     return self.attach_provider(db, user_id, mc_uuid, provider_uuid)

    # def attach_provider(
    #     self,
    #     db: Session,
    #     user_id: int,
    #     mc_uuid: UUID,
    #     provider_uuid: UUID | None,
    # ) -> Microcontroller:
    #     microcontroller = self._ensure_microcontroller(db, user_id, mc_uuid)

    #     if provider_uuid is None:
    #         if microcontroller.power_provider_id:
    #             previous = self._provider_repo(db).get_for_user(
    #                 microcontroller.power_provider_id, user_id
    #             )
    #             if previous:
    #                 previous.enabled = False
    #         for sensor_provider in microcontroller.sensor_providers:
    #             sensor_provider.enabled = False
    #         microcontroller.power_provider_id = None
    #         db.commit()
    #         db.refresh(microcontroller)
    #         return microcontroller

    #     provider = self._provider_repo(db).get_for_user_by_uuid(provider_uuid, user_id)
    #     if not provider:
    #         raise HTTPException(
    #             status_code=status.HTTP_404_NOT_FOUND,
    #             detail="Provider not found",
    #         )

    #     if provider.provider_type == ProviderType.SENSOR:
    #         if not microcontroller.assigned_sensors:
    #             raise HTTPException(
    #                 status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
    #                 detail="Sensor providers require assigned sensors",
    #             )
    #         sensor_type = resolve_sensor_type(provider.vendor)
    #         if not sensor_type or sensor_type not in microcontroller.assigned_sensors:
    #             raise HTTPException(
    #                 status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
    #                 detail="Sensor provider is not supported by this microcontroller",
    #             )
    #     elif provider.provider_type == ProviderType.API:
    #         if provider.kind != ProviderKind.POWER:
    #             raise HTTPException(
    #                 status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
    #                 detail="Only API power providers can be attached",
    #             )
    #     else:
    #         raise HTTPException(
    #             status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
    #             detail="Manual/scheduled provider is selected by detaching providers",
    #         )

    #     if microcontroller.power_provider_id and microcontroller.power_provider_id != provider.id:
    #         previous = self._provider_repo(db).get_for_user(
    #             microcontroller.power_provider_id, user_id
    #         )
    #         if previous:
    #             previous.enabled = False

    #     microcontroller.power_provider_id = provider.id
    #     for sensor_provider in microcontroller.sensor_providers:
    #         if sensor_provider.id != provider.id:
    #             sensor_provider.enabled = False
    #     # Attaching explicitly enables the selected provider and disables the previous one.
    #     provider.enabled = True
    #     db.commit()
    #     db.refresh(microcontroller)
    #     action = "detached" if provider_uuid is None else "attached"
    #     self.logger.info(
    #         "Microcontroller provider updated",
    #         extra={
    #             "user_id": user_id,
    #             "microcontroller_uuid": microcontroller.uuid,
    #             "action": action,
    #             "provider_uuid": provider_uuid,
    #         },
    #     )
    #     return microcontroller

    # def set_assigned_sensors(
    #     self,
    #     db: Session,
    #     user_id: int,
    #     mc_uuid: UUID,
    #     assigned_sensors: list,
    # ) -> Microcontroller:
    #     normalized_sensors = self._normalize_sensor_values(assigned_sensors)
    #     if len(set(normalized_sensors)) != len(normalized_sensors):
    #         raise HTTPException(
    #             status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
    #             detail="assigned_sensors must not contain duplicates",
    #         )

    #     microcontroller = self._ensure_microcontroller(db, user_id, mc_uuid)
    #     microcontroller.sensor_capabilities = [
    #         MicrocontrollerSensorCapability(sensor_type=sensor_type)
    #         for sensor_type in normalized_sensors
    #     ]
    #     db.commit()
    #     db.refresh(microcontroller)
    #     self.logger.info(
    #         "Assigned sensors updated",
    #         extra={
    #             "user_id": user_id,
    #             "microcontroller_uuid": microcontroller.uuid,
    #             "assigned_sensors": normalized_sensors,
    #         },
    #     )
    #     return microcontroller

    # def delete_for_user(self, db: Session, user_id: int, mc_uuid: UUID) -> None:
    #     deleted = self._repo(db).delete_for_user(mc_uuid, user_id)
    #     if not deleted:
    #         raise HTTPException(
    #             status_code=status.HTTP_404_NOT_FOUND,
    #             detail="Microcontroller not found",
    #         )
    #     db.commit()
    #     self.logger.info(
    #         "Microcontroller deleted by admin",
    #         extra={"user_id": user_id, "microcontroller_uuid": mc_uuid},
    #     )
