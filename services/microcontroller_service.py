import logging
from typing import Any, Callable, Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from smart_common.core import db
from smart_common.enums.event import EventType
from smart_common.models.microcontroller import Microcontroller
from smart_common.models.microcontroller_sensor_capability import (
    MicrocontrollerSensorCapability,
)
from smart_common.enums.sensor import SensorType
from smart_common.nats.client import NATSClient
from smart_common.nats.event_helpers import stream_name
from smart_common.nats.publisher import NatsPublisher
from smart_common.providers.enums import ProviderKind, ProviderType
from smart_common.providers.registry import resolve_sensor_type
from smart_common.repositories.microcontroller import MicrocontrollerRepository
from smart_common.repositories.provider import ProviderRepository
from smart_common.schemas.microcontroller_schema import (
    MicrocontrollerConfigUpdateRequest,
)
from smart_common.events.event_dispatcher import EventDispatcher


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

    def register_microcontroller_admin(
        self,
        db: Session,
        *,
        payload: dict,
    ) -> Microcontroller:
        assigned_sensors = self._normalize_sensor_values(
            payload.pop("assigned_sensors", []) or []
        )

        if len(set(assigned_sensors)) != len(assigned_sensors):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="assigned_sensors must not contain duplicates",
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

        microcontroller.config = {
            "uuid": str(microcontroller.uuid),
            "device_max": microcontroller.max_devices,
            "active_low": False,
            "devices_config": [],
            "provider": None,
        }

        db.commit()
        db.refresh(microcontroller)

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

        for field, value in data.items():
            if field in repo.ADMIN_UPDATE_FIELDS:
                setattr(microcontroller, field, value)

        if assigned_sensors is not None:
            normalized = self._normalize_sensor_values(assigned_sensors)

            if len(set(normalized)) != len(normalized):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="assigned_sensors must not contain duplicates",
                )

            microcontroller.sensor_capabilities.clear()
            db.flush()

            microcontroller.sensor_capabilities.extend(
                MicrocontrollerSensorCapability(sensor_type=s) for s in normalized
            )

        config = microcontroller.config or {}

        config["uuid"] = str(microcontroller.uuid)
        config.pop("device_uuid", None)

        if "max_devices" in data:
            config["device_max"] = microcontroller.max_devices

        config.setdefault("active_low", False)
        config.setdefault("devices_config", [])
        config.setdefault("provider", None)

        microcontroller.config = config

        db.commit()
        db.refresh(microcontroller)

        self.logger.info(
            "Microcontroller updated by admin",
            extra={
                "microcontroller_id": microcontroller.id,
                "fields": list(data.keys()),
                "assigned_sensors": assigned_sensors,
            },
        )

        return microcontroller

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

        next_provider_id: int | None = None
        next_provider_uuid = str(provider_uuid) if provider_uuid is not None else None

        if provider_uuid is not None:
            provider = self._provider_repo(db).get_for_user_by_uuid(provider_uuid, user_id)
            if not provider or not provider.enabled:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Provider not found or not available",
                )
            next_provider_id = provider.id
            next_provider_uuid = str(provider.uuid)

        if previous_provider_uuid == next_provider_uuid:
            self.logger.info(
                "Provider already set for microcontroller",
                extra={
                    "microcontroller_uuid": str(microcontroller.uuid),
                    "provider_uuid": next_provider_uuid,
                },
            )
            return microcontroller

        ack_data = await self._publish_provider_updated(
            microcontroller_uuid=str(microcontroller.uuid),
            provider_uuid=next_provider_uuid,
            previous_provider_uuid=previous_provider_uuid,
        )

        microcontroller.power_provider_id = next_provider_id
        db.commit()
        db.refresh(microcontroller)

        self.logger.info(
            "Provider updated for microcontroller",
            extra={
                "microcontroller_uuid": str(microcontroller.uuid),
                "previous_provider_uuid": previous_provider_uuid,
                "provider_uuid": next_provider_uuid,
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
    ) -> dict:
        event_type = EventType.PROVIDER_UPDATED
        subject = f"{stream_name()}.{microcontroller_uuid}.command.provider_updated"
        ack_subject = f"{stream_name()}.provider_update.ack"
        try:
            result = await self.events.publish_event_and_wait_for_ack(
                entity_type="microcontroller",
                entity_id=microcontroller_uuid,
                event_type=event_type,
                data={"provider_uuid": provider_uuid},
                predicate=lambda payload: self._provider_updated_ack_matches(
                    payload=payload,
                    microcontroller_uuid=microcontroller_uuid,
                    provider_uuid=provider_uuid,
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

        if ack_data.get("changed") is not True:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Agent did not confirm provider change",
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

        return ack_data

    def _provider_updated_ack_matches(
        self,
        *,
        payload: dict,
        microcontroller_uuid: str,
        provider_uuid: str | None,
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
            return incoming_provider_uuid is None
        return str(incoming_provider_uuid) == provider_uuid

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
