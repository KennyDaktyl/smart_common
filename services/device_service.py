import logging
from datetime import datetime, timezone
from typing import Callable
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from smart_common.core.db import transactional_session
from smart_common.enums.device import DeviceMode
from smart_common.enums.device_dependency import DeviceDependencyAction
from smart_common.enums.event import EventType
from smart_common.enums.scheduler import SchedulerControlMode, SchedulerPolicyType
from smart_common.enums.sensor import SensorType
from smart_common.enums.user import UserRole
from smart_common.events.device_events import (
    DeviceCommandPayload,
    DeviceCreatedPayload,
    DeviceDeletePayload,
    DeviceUpdatedPayload,
)
from smart_common.events.event_dispatcher import EventDispatcher
from smart_common.models.device import Device
from smart_common.models.microcontroller import Microcontroller
from smart_common.nats.client import NATSClient
from smart_common.nats.event_helpers import ack_subject_for_entity, subject_for_entity
from smart_common.nats.publisher import NatsPublisher
from smart_common.repositories.device import DeviceRepository
from smart_common.repositories.microcontroller import MicrocontrollerRepository
from smart_common.repositories.scheduler import SchedulerRepository
from smart_common.schemas.automation_rule import (
    AutomationRuleGroup,
    AutomationRuleSource,
    build_legacy_power_rule,
    extract_legacy_power_threshold,
    uses_source,
)
from smart_common.schemas.device_schema import DeviceListQuery, DeviceResponse
from smart_common.schemas.device_dependency import (
    DeviceDependencyRule,
    parse_device_dependency_rule,
)
from smart_common.schemas.scheduler_policy import SchedulerControlPolicy

logger = logging.getLogger(__name__)

TEMPERATURE_SENSOR_CAPABILITIES = {
    SensorType.DS18B20.value,
    "temperature",
}


def _provider_power_unit(microcontroller: Microcontroller) -> str:
    provider = microcontroller.power_provider
    if provider is None or provider.unit is None:
        return "W"
    if hasattr(provider.unit, "value"):
        return str(provider.unit.value)
    return str(provider.unit)


def _normalize_auto_rule(
    *,
    auto_rule: AutomationRuleGroup | dict | None,
    threshold_value: float | None,
    microcontroller: Microcontroller,
) -> AutomationRuleGroup | None:
    normalized_rule: AutomationRuleGroup | None
    if isinstance(auto_rule, AutomationRuleGroup):
        normalized_rule = auto_rule
    elif isinstance(auto_rule, dict):
        normalized_rule = AutomationRuleGroup.model_validate(auto_rule)
    else:
        normalized_rule = None

    if normalized_rule is not None:
        return normalized_rule
    if threshold_value is None:
        return None

    return build_legacy_power_rule(
        value=float(threshold_value),
        unit=_provider_power_unit(microcontroller),
    )


def _rule_from_value(value: AutomationRuleGroup | dict | None) -> AutomationRuleGroup | None:
    if isinstance(value, AutomationRuleGroup):
        return value
    if isinstance(value, dict):
        try:
            return AutomationRuleGroup.model_validate(value)
        except Exception:
            return None
    return None


def _scheduler_policy_from_value(value: SchedulerControlPolicy | dict | None) -> (
    SchedulerControlPolicy | None
):
    if isinstance(value, SchedulerControlPolicy):
        return value
    if isinstance(value, dict):
        try:
            return SchedulerControlPolicy.model_validate(value)
        except Exception:
            return None
    return None


def _microcontroller_has_temperature_sensor(microcontroller: Microcontroller) -> bool:
    assigned_sensors = {
        str(sensor).strip().lower()
        for sensor in getattr(microcontroller, "assigned_sensors", []) or []
        if str(sensor).strip()
    }
    return bool(assigned_sensors & TEMPERATURE_SENSOR_CAPABILITIES)


def _slot_uses_temperature_policy(slot) -> bool:
    control_mode = getattr(slot, "control_mode", SchedulerControlMode.DIRECT)
    control_mode_value = getattr(control_mode, "value", control_mode)
    if control_mode_value != SchedulerControlMode.POLICY.value:
        return False

    policy = _scheduler_policy_from_value(getattr(slot, "control_policy_json", None))
    if policy is None:
        return False

    return policy.policy_type == SchedulerPolicyType.TEMPERATURE_HYSTERESIS


def _dependency_rule_from_value(
    value: DeviceDependencyRule | dict | None,
) -> DeviceDependencyRule | None:
    return parse_device_dependency_rule(value)


def _dependency_rule_is_effective(rule: DeviceDependencyRule | None) -> bool:
    if rule is None:
        return False
    return (
        rule.when_source_on != DeviceDependencyAction.NONE
        or rule.when_source_off != DeviceDependencyAction.NONE
    )


def _slot_dependency_rule(slot) -> DeviceDependencyRule | None:
    return _dependency_rule_from_value(getattr(slot, "device_dependency_rule_json", None))


class DeviceService:
    def __init__(
        self,
        repo_factory: Callable[[Session], DeviceRepository],
        microcontroller_repo_factory: Callable[[Session], MicrocontrollerRepository],
        scheduler_repo_factory: Callable[[Session], SchedulerRepository] | None = None,
    ):
        self._repo_factory = repo_factory
        self._microcontroller_repo_factory = microcontroller_repo_factory
        self._scheduler_repo_factory = scheduler_repo_factory
        self.logger = logger
        self.events = EventDispatcher(NatsPublisher(NATSClient()))

    # ---------------------------------------------------------------------
    # Repositories
    # ---------------------------------------------------------------------

    def _repo(self, db: Session) -> DeviceRepository:
        return self._repo_factory(db)

    def _microcontroller_repo(self, db: Session) -> MicrocontrollerRepository:
        return self._microcontroller_repo_factory(db)

    def _scheduler_repo(self, db: Session) -> SchedulerRepository:
        if not self._scheduler_repo_factory:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Scheduler repository is not configured",
            )
        return self._scheduler_repo_factory(db)

    # ---------------------------------------------------------------------
    # Guards
    # ---------------------------------------------------------------------

    def _ensure_microcontroller(
        self, db: Session, user_id: int, mc_uuid: UUID
    ) -> Microcontroller:
        self.logger.debug(
            "Ensure microcontroller | user_id=%s mc_uuid=%s",
            user_id,
            mc_uuid,
        )

        microcontroller = self._microcontroller_repo(db).get_for_user_by_uuid(
            mc_uuid, user_id
        )

        if not microcontroller:
            self.logger.warning(
                "Microcontroller NOT FOUND | user_id=%s mc_uuid=%s",
                user_id,
                mc_uuid,
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Microcontroller not found",
            )

        return microcontroller

    def _ensure_device_belongs_to_microcontroller(
        self, device: Device, microcontroller_id: int
    ) -> None:
        if device.microcontroller_id != microcontroller_id:
            self.logger.warning(
                "Device does not belong to microcontroller | device_number=%s mc_id=%s",
                device.device_number,
                microcontroller_id,
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Device not found for the selected microcontroller",
            )

    def _ensure_target_device(
        self,
        *,
        db: Session,
        user_id: int,
        target_device_id: int,
    ) -> Device:
        target_device = self._repo(db).get_for_user_by_id(target_device_id, user_id)
        if not target_device:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dependency target device not found",
            )
        return target_device

    def _normalize_dependency_rule(
        self,
        *,
        db: Session,
        user_id: int,
        raw_rule: DeviceDependencyRule | dict | None,
        source_microcontroller: Microcontroller | None,
        source_device: Device | None,
    ) -> DeviceDependencyRule | None:
        dependency_rule = _dependency_rule_from_value(raw_rule)
        if not _dependency_rule_is_effective(dependency_rule):
            return None
        if dependency_rule is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invalid device dependency rule",
            )

        target_device = self._ensure_target_device(
            db=db,
            user_id=user_id,
            target_device_id=dependency_rule.target_device_id,
        )

        if source_device is not None and target_device.id == source_device.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Device dependency target cannot be the same as the source device",
            )

        if (
            source_microcontroller is not None
            and target_device.microcontroller_id != source_microcontroller.id
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Dependency target device must belong to the same microcontroller",
            )

        return dependency_rule.model_copy(
            update={"target_device_number": target_device.device_number}
        )

    def _iter_other_inbound_dependency_targets(
        self,
        *,
        microcontroller: Microcontroller,
        exclude_source_device_id: int | None,
    ):
        for device in getattr(microcontroller, "devices", []) or []:
            if exclude_source_device_id is not None and device.id == exclude_source_device_id:
                continue

            auto_rule = _dependency_rule_from_value(
                getattr(device, "device_dependency_rule_json", None)
            )
            if _dependency_rule_is_effective(auto_rule):
                yield ("AUTO", device, auto_rule)

            scheduler = getattr(device, "scheduler", None)
            if scheduler is None or getattr(device, "mode", None) != DeviceMode.SCHEDULE:
                continue

            for slot in getattr(scheduler, "slots", []) or []:
                slot_rule = _slot_dependency_rule(slot)
                if _dependency_rule_is_effective(slot_rule):
                    yield ("SCHEDULER", device, slot_rule)

    def _ensure_dependency_target_is_available(
        self,
        *,
        microcontroller: Microcontroller,
        candidate_rules: list[DeviceDependencyRule],
        exclude_source_device_id: int | None,
    ) -> None:
        candidate_target_ids = {rule.target_device_id for rule in candidate_rules}
        if not candidate_target_ids:
            return

        for source_kind, source_device, active_rule in self._iter_other_inbound_dependency_targets(
            microcontroller=microcontroller,
            exclude_source_device_id=exclude_source_device_id,
        ):
            if active_rule.target_device_id not in candidate_target_ids:
                continue
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Dependency target device is already controlled by another "
                    f"{source_kind.lower()} source on this microcontroller"
                ),
            )

    def _ensure_auto_rule_for_mode(
        self,
        *,
        microcontroller: Microcontroller,
        new_mode: DeviceMode | None,
        new_threshold: float | None,
        new_auto_rule: AutomationRuleGroup | dict | None,
        current_device: Device | None = None,
    ) -> AutomationRuleGroup | None:
        effective_mode = new_mode or (current_device.mode if current_device else None)
        effective_threshold = new_threshold
        if effective_threshold is None and current_device is not None:
            effective_threshold = (
                float(current_device.threshold_value)
                if current_device.threshold_value is not None
                else None
            )

        effective_auto_rule = _normalize_auto_rule(
            auto_rule=(
                new_auto_rule
                if new_auto_rule is not None
                else (current_device.auto_rule_json if current_device else None)
            ),
            threshold_value=effective_threshold,
            microcontroller=microcontroller,
        )

        if effective_mode == DeviceMode.AUTO_POWER and microcontroller.power_provider is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Auto mode requires a power provider attached to the microcontroller",
            )

        if effective_mode == DeviceMode.AUTO_POWER and effective_auto_rule is None:
            self.logger.warning(
                "AUTO mode without rule | device_id=%s",
                getattr(current_device, "id", None),
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="threshold_value or auto_rule is required when device mode is AUTO",
            )

        if (
            effective_auto_rule is not None
            and uses_source(
                effective_auto_rule,
                AutomationRuleSource.PROVIDER_BATTERY_SOC,
            )
            and not bool(getattr(microcontroller.power_provider, "has_energy_storage", False))
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Selected provider does not support battery state-of-charge rules",
            )

        return effective_auto_rule

    def _ensure_scheduler_for_mode(
        self,
        *,
        db: Session,
        user_id: int,
        microcontroller: Microcontroller,
        new_mode: DeviceMode | None,
        scheduler_in_payload: bool,
        new_scheduler_id: int | None,
        current_device: Device | None = None,
    ) -> None:
        effective_mode = new_mode or (current_device.mode if current_device else None)
        effective_scheduler_id = (
            new_scheduler_id
            if scheduler_in_payload
            else (current_device.scheduler_id if current_device else None)
        )

        if effective_scheduler_id is not None:
            scheduler = self._scheduler_repo(db).get_for_user_by_id(
                effective_scheduler_id, user_id
            )
            if not scheduler:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Scheduler not found",
                )
            for slot in getattr(scheduler, "slots", []):
                rule = _rule_from_value(getattr(slot, "activation_rule_json", None))
                if uses_source(
                    rule,
                    AutomationRuleSource.PROVIDER_BATTERY_SOC,
                ) and not bool(
                    getattr(microcontroller.power_provider, "has_energy_storage", False)
                ):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Selected provider does not support battery state-of-charge scheduler rules",
                    )
                if _slot_uses_temperature_policy(slot) and not _microcontroller_has_temperature_sensor(
                    microcontroller
                ):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=(
                            "Selected microcontroller does not provide a temperature "
                            "sensor required by this scheduler"
                        ),
                    )
                slot_dependency_rule = _slot_dependency_rule(slot)
                if _dependency_rule_is_effective(slot_dependency_rule):
                    normalized_slot_rule = self._normalize_dependency_rule(
                        db=db,
                        user_id=user_id,
                        raw_rule=slot_dependency_rule,
                        source_microcontroller=microcontroller,
                        source_device=current_device,
                    )
                    if normalized_slot_rule is not None:
                        self._ensure_dependency_target_is_available(
                            microcontroller=microcontroller,
                            candidate_rules=[normalized_slot_rule],
                            exclude_source_device_id=getattr(current_device, "id", None),
                        )

        if effective_mode == DeviceMode.SCHEDULE and effective_scheduler_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="scheduler_id is required when device mode is SCHEDULE",
            )

    # ---------------------------------------------------------------------
    # Queries
    # ---------------------------------------------------------------------

    def list_devices(
        self,
        *,
        db: Session,
        user_id: int,
        user_role: UserRole,
        query: DeviceListQuery,
    ):
        self.logger.info(
            "LIST devices | user_id=%s role=%s admin=%s",
            user_id,
            user_role,
            query.is_admin,
        )

        repo = self._repo(db)

        if query.is_admin and user_role == UserRole.ADMIN:
            items = repo.list(
                limit=query.limit,
                offset=query.offset,
                order_by=repo.model.id.asc(),
            )
            total = repo.count()
        else:
            items = repo.list_for_user(user_id=user_id)
            total = len(items)

        self.logger.debug(
            "LIST devices result | user_id=%s count=%s",
            user_id,
            total,
        )

        return items, total

    def get_device(self, db: Session, device_id: int, user_id: int) -> Device:
        self.logger.debug(
            "GET device | device_id=%s user_id=%s",
            device_id,
            user_id,
        )

        device = self._repo(db).get_for_user_by_id(device_id, user_id)

        if not device:
            self.logger.warning(
                "Device NOT FOUND | device_id=%s user_id=%s",
                device_id,
                user_id,
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Device not found",
            )

        return device

    def list_for_microcontroller(
        self, db: Session, user_id: int, mc_uuid: UUID
    ) -> list[Device]:
        self.logger.info(
            "LIST devices for microcontroller | user_id=%s mc_uuid=%s",
            user_id,
            mc_uuid,
        )

        microcontroller = self._ensure_microcontroller(db, user_id, mc_uuid)
        devices = self._repo(db).get_for_microcontroller(microcontroller.id, user_id)

        self.logger.debug(
            "LIST devices for microcontroller result | mc_uuid=%s count=%s",
            mc_uuid,
            len(devices),
        )

        return devices

    # ---------------------------------------------------------------------
    # Commands
    # ---------------------------------------------------------------------

    async def create_device(
        self, db: Session, user_id: int, mc_uuid: UUID, payload: dict
    ) -> Device:
        self.logger.info(
            "CREATE device | user_id=%s mc_uuid=%s",
            user_id,
            mc_uuid,
        )
        self.logger.debug("CREATE device payload | %s", payload)

        microcontroller = self._ensure_microcontroller(db, user_id, mc_uuid)

        async with transactional_session(db):
            repo = self._repo(db)

            devices_count = repo.count_for_microcontroller(microcontroller.id)
            self.logger.debug(
                "Microcontroller devices count | mc_id=%s count=%s max=%s",
                microcontroller.id,
                devices_count,
                microcontroller.max_devices,
            )

            if devices_count >= microcontroller.max_devices:
                self.logger.warning(
                    "Max devices exceeded | mc_id=%s",
                    microcontroller.id,
                )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        f"Microcontroller supports max "
                        f"{microcontroller.max_devices} devices"
                    ),
                )

            effective_auto_rule = self._ensure_auto_rule_for_mode(
                microcontroller=microcontroller,
                new_mode=payload.get("mode"),
                new_threshold=payload.get("threshold_value"),
                new_auto_rule=payload.get("auto_rule"),
            )
            effective_dependency_rule = self._normalize_dependency_rule(
                db=db,
                user_id=user_id,
                raw_rule=payload.get("device_dependency_rule"),
                source_microcontroller=microcontroller,
                source_device=None,
            )
            if effective_dependency_rule is not None:
                self._ensure_dependency_target_is_available(
                    microcontroller=microcontroller,
                    candidate_rules=[effective_dependency_rule],
                    exclude_source_device_id=None,
                )
            self._ensure_scheduler_for_mode(
                db=db,
                user_id=user_id,
                microcontroller=microcontroller,
                new_mode=payload.get("mode"),
                scheduler_in_payload="scheduler_id" in payload,
                new_scheduler_id=payload.get("scheduler_id"),
            )

            data = dict(payload)
            data["microcontroller_id"] = microcontroller.id
            data["auto_rule_json"] = (
                effective_auto_rule.model_dump() if effective_auto_rule is not None else None
            )
            data["device_dependency_rule_json"] = (
                effective_dependency_rule.model_dump(mode="json")
                if effective_dependency_rule is not None
                else None
            )
            legacy_threshold = extract_legacy_power_threshold(effective_auto_rule)
            data["threshold_value"] = (
                legacy_threshold[0] if legacy_threshold is not None else None
            )
            data.pop("auto_rule", None)
            data.pop("device_dependency_rule", None)

            device = repo.create(data)
            if not isinstance(device.manual_state, bool):
                device.manual_state = False
            self._sync_device_config_state(
                device,
                is_on=(
                    device.manual_state
                    if isinstance(device.manual_state, bool)
                    else None
                ),
            )

            self.logger.info(
                "Device CREATED | device_id=%s mc_uuid=%s",
                device.id,
                microcontroller.uuid,
            )

            ack_data = await self._publish_event(
                microcontroller_uuid=microcontroller.uuid,
                event_type=EventType.DEVICE_CREATED,
                payload=DeviceCreatedPayload(
                    device_id=device.id,
                    device_uuid=str(device.uuid),
                    device_number=device.device_number,
                    mode=device.mode.value,
                    rated_power=device.rated_power,
                    threshold_value=device.threshold_value,
                    threshold_unit=_provider_power_unit(microcontroller),
                    auto_rule=_rule_from_value(device.auto_rule_json),
                    device_dependency_rule=_dependency_rule_from_value(
                        device.device_dependency_rule_json
                    ),
                    scheduler_id=device.scheduler_id,
                    microcontroller_uuid=str(microcontroller.uuid),
                ),
            )

            ack_state = self.ack_device_state(ack_data)
            if ack_state is not None:
                device.manual_state = ack_state
                device.last_state_change_at = datetime.now(timezone.utc)
                self._sync_device_config_state(device, is_on=ack_state)

            return device

    async def update_device(
        self,
        db: Session,
        user_id: int,
        device_id: int,
        payload: dict,
        microcontroller_id: int | None = None,
    ) -> Device:
        self.logger.info(
            "UPDATE device | device_id=%s user_id=%s",
            device_id,
            user_id,
        )
        self.logger.debug("UPDATE device payload | %s", payload)

        device = self.get_device(db, device_id, user_id)

        async with transactional_session(db):
            effective_auto_rule = self._ensure_auto_rule_for_mode(
                microcontroller=device.microcontroller,
                new_mode=payload.get("mode"),
                new_threshold=payload.get("threshold_value"),
                new_auto_rule=payload.get("auto_rule"),
                current_device=device,
            )
            effective_dependency_rule = self._normalize_dependency_rule(
                db=db,
                user_id=user_id,
                raw_rule=(
                    payload.get("device_dependency_rule")
                    if "device_dependency_rule" in payload
                    else getattr(device, "device_dependency_rule_json", None)
                ),
                source_microcontroller=device.microcontroller,
                source_device=device,
            )
            if effective_dependency_rule is not None:
                self._ensure_dependency_target_is_available(
                    microcontroller=device.microcontroller,
                    candidate_rules=[effective_dependency_rule],
                    exclude_source_device_id=device.id,
                )
            self._ensure_scheduler_for_mode(
                db=db,
                user_id=user_id,
                microcontroller=device.microcontroller,
                new_mode=payload.get("mode"),
                scheduler_in_payload="scheduler_id" in payload,
                new_scheduler_id=payload.get("scheduler_id"),
                current_device=device,
            )

            if microcontroller_id is not None:
                self._ensure_device_belongs_to_microcontroller(
                    device, microcontroller_id
                )

            payload = dict(payload)
            payload["auto_rule_json"] = (
                effective_auto_rule.model_dump() if effective_auto_rule is not None else None
            )
            payload["device_dependency_rule_json"] = (
                effective_dependency_rule.model_dump(mode="json")
                if effective_dependency_rule is not None
                else None
            )
            legacy_threshold = extract_legacy_power_threshold(effective_auto_rule)
            payload["threshold_value"] = (
                legacy_threshold[0] if legacy_threshold is not None else None
            )
            payload.pop("auto_rule", None)
            payload.pop("device_dependency_rule", None)

            updated = self._repo(db).update_for_user(device_id, user_id, payload)
            self._sync_device_config_state(
                updated,
                is_on=(
                    updated.manual_state
                    if isinstance(updated.manual_state, bool)
                    else None
                ),
            )

            self.logger.info(
                "Device UPDATED | device_id=%s",
                updated.id,
            )

            await self._publish_event(
                microcontroller_uuid=device.microcontroller.uuid,
                event_type=EventType.DEVICE_UPDATED,
                payload=DeviceUpdatedPayload(
                    device_id=updated.id,
                    device_uuid=str(updated.uuid),
                    device_number=updated.device_number,
                    mode=updated.mode.value,
                    rated_power=updated.rated_power,
                    threshold_value=updated.threshold_value,
                    threshold_unit=_provider_power_unit(device.microcontroller),
                    auto_rule=_rule_from_value(updated.auto_rule_json),
                    device_dependency_rule=_dependency_rule_from_value(
                        updated.device_dependency_rule_json
                    ),
                    scheduler_id=updated.scheduler_id,
                ),
            )

            return updated

    async def delete_device(
        self,
        db: Session,
        user_id: int,
        device_id: int,
        microcontroller_id: int | None = None,
    ) -> None:
        self.logger.info(
            "DELETE device | device_id=%s user_id=%s",
            device_id,
            user_id,
        )

        device = self.get_device(db, device_id, user_id)

        async with transactional_session(db):
            if microcontroller_id is not None:
                self._ensure_device_belongs_to_microcontroller(
                    device, microcontroller_id
                )

            await self._publish_event(
                microcontroller_uuid=device.microcontroller.uuid,
                event_type=EventType.DEVICE_DELETED,
                payload=DeviceDeletePayload(
                    device_id=device_id,
                    device_uuid=str(device.uuid),
                    device_number=device.device_number,
                ),
            )

            self._repo(db).delete(device)

            self.logger.info(
                "Device DELETED | device_id=%s",
                device.id,
            )

    async def set_manual_state(
        self,
        *,
        db: Session,
        user_id: int,
        device_id: int,
        state: bool,
    ) -> tuple[DeviceResponse, bool]:

        device = self.get_device(db, device_id, user_id)
        device_dto = DeviceResponse.model_validate(device, from_attributes=True)

        try:
            async with transactional_session(db):
                device.mode = DeviceMode.MANUAL
                device.manual_state = state
                device.last_state_change_at = datetime.now(timezone.utc)

                ack_data = await self._publish_event(
                    microcontroller_uuid=device.microcontroller.uuid,
                    event_type=EventType.DEVICE_COMMAND,
                    payload=DeviceCommandPayload(
                        device_id=device_id,
                        device_uuid=str(device.uuid),
                        device_number=device.device_number,
                        command="SET_STATE",
                        mode="MANUAL",
                        is_on=state,
                    ),
                )

                ack_state = self.ack_device_state(ack_data)
                if ack_state is not None:
                    device.manual_state = ack_state

                if isinstance(device.manual_state, bool):
                    self._sync_device_config_state(device, is_on=device.manual_state)

                device_dto = DeviceResponse.model_validate(device, from_attributes=True)
            return device_dto, True

        except HTTPException as exc:
            self.logger.warning(
                "SET MANUAL STATE – ACK FAILED | device_id=%s | %s",
                device_id,
                exc,
            )
            return device_dto, False

    # ---------------------------------------------------------------------
    # Events
    # ---------------------------------------------------------------------

    def ack_device_id(self, event: dict) -> int | None:
        self.logger.warning("RAW ACK EVENT: %s", event)

        data = event.get("data") or {}

        if isinstance(data, dict) and "device_id" in data:
            return data["device_id"]

        ack = data.get("ack")
        if isinstance(ack, dict) and "device_id" in ack:
            return ack["device_id"]

        return None

    def ack_device_state(self, ack_data: dict) -> bool | None:
        if not isinstance(ack_data, dict):
            return None

        sources = [ack_data]
        nested_ack = ack_data.get("ack")
        if isinstance(nested_ack, dict):
            sources.insert(0, nested_ack)

        for source in sources:
            for key in ("is_on", "actual_state"):
                value = source.get(key)
                if isinstance(value, bool):
                    return value

        return None

    def _sync_device_config_state(
        self,
        device: Device,
        *,
        is_on: bool | None,
    ) -> None:
        microcontroller = getattr(device, "microcontroller", None)
        if not microcontroller:
            return

        config = dict(microcontroller.config or {})
        raw_devices_config = config.get("devices_config")

        devices_config = (
            [dict(item) for item in raw_devices_config if isinstance(item, dict)]
            if isinstance(raw_devices_config, list)
            else []
        )

        updated = False
        for item in devices_config:
            if (
                item.get("device_id") == device.id
                or item.get("pin_number") == device.device_number
            ):
                mode_value = (
                    device.mode.value
                    if hasattr(device.mode, "value")
                    else str(device.mode)
                )
                threshold_value = (
                    float(device.threshold_value)
                    if device.threshold_value is not None
                    else None
                )
                threshold_unit = _provider_power_unit(microcontroller)
                auto_rule = _rule_from_value(device.auto_rule_json)
                dependency_rule = _dependency_rule_from_value(
                    device.device_dependency_rule_json
                )
                rated_power = (
                    float(device.rated_power) if device.rated_power is not None else None
                )
                item["device_id"] = device.id
                item["device_uuid"] = str(device.uuid)
                item["device_number"] = device.device_number
                item["pin_number"] = device.device_number
                item["mode"] = mode_value
                item["rated_power"] = rated_power
                item["threshold_value"] = threshold_value
                item["threshold_unit"] = threshold_unit
                item["auto_rule"] = (
                    auto_rule.model_dump() if auto_rule is not None else None
                )
                item["device_dependency_rule"] = (
                    dependency_rule.model_dump(mode="json")
                    if dependency_rule is not None
                    else None
                )
                if is_on is not None:
                    item["is_on"] = is_on
                elif "is_on" not in item and isinstance(device.manual_state, bool):
                    item["is_on"] = device.manual_state
                updated = True

        if not updated:
            mode_value = (
                device.mode.value if hasattr(device.mode, "value") else str(device.mode)
            )
            threshold_value = (
                float(device.threshold_value)
                if device.threshold_value is not None
                else None
            )
            threshold_unit = _provider_power_unit(microcontroller)
            auto_rule = _rule_from_value(device.auto_rule_json)
            dependency_rule = _dependency_rule_from_value(device.device_dependency_rule_json)
            rated_power = (
                float(device.rated_power) if device.rated_power is not None else None
            )
            devices_config.append(
                {
                    "device_id": device.id,
                    "device_uuid": str(device.uuid),
                    "device_number": device.device_number,
                    "pin_number": device.device_number,
                    "mode": mode_value,
                    "rated_power": rated_power,
                    "threshold_value": threshold_value,
                    "threshold_unit": threshold_unit,
                    "auto_rule": (
                        auto_rule.model_dump() if auto_rule is not None else None
                    ),
                    "device_dependency_rule": (
                        dependency_rule.model_dump(mode="json")
                        if dependency_rule is not None
                        else None
                    ),
                    "is_on": (
                        is_on
                        if is_on is not None
                        else (device.manual_state if isinstance(device.manual_state, bool) else None)
                    ),
                }
            )

        config["devices_config"] = devices_config
        microcontroller.config = config

    async def _publish_event(
        self, microcontroller_uuid: UUID, event_type: EventType, payload
    ) -> dict:
        subject = subject_for_entity(microcontroller_uuid, event_type.value)
        self.logger.info("Subject: %s", subject)
        ack_subject = ack_subject_for_entity(microcontroller_uuid, event_type.value)
        self.logger.info("Subject ACK: %s", ack_subject)
        self.logger.debug(
            "PUBLISH event | type=%s mc_uuid=%s subject=%s ack_subject=%s payload=%s",
            event_type,
            microcontroller_uuid,
            subject,
            ack_subject,
            payload,
        )

        try:
            result = await self.events.publish_event_and_wait_for_ack(
                entity_type=event_type.value,
                entity_id=str(microcontroller_uuid),
                event_type=event_type,
                data=payload,
                predicate=lambda e: self.ack_device_id(e) == payload.device_id,
                timeout=10.0,
                subject=subject,
                ack_subject=ack_subject,
            )

            ack_data = result.get("data") or {}
            if not ack_data.get("ok", False):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Agent rejected {event_type.value} event",
                )

            self.logger.debug(
                "EVENT ACK received | type=%s mc_uuid=%s device_id=%s",
                event_type,
                microcontroller_uuid,
                payload.device_id,
            )
            return ack_data

        except Exception as exc:
            self.logger.error(
                "EVENT ACK FAILED | type=%s mc_uuid=%s error=%s",
                event_type,
                microcontroller_uuid,
                exc,
                exc_info=True,
            )
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail=(
                    f"Microcontroller did not acknowledge "
                    f"the {event_type.value} event: {exc}"
                ),
            ) from exc
