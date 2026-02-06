from datetime import datetime, timezone
import logging
from typing import Callable
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from smart_common.core.db import transactional_session
from smart_common.enums.device import DeviceMode
from smart_common.enums.event import EventType
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
from smart_common.schemas.device_schema import DeviceListQuery, DeviceResponse

logger = logging.getLogger(__name__)


class DeviceService:
    def __init__(
        self,
        repo_factory: Callable[[Session], DeviceRepository],
        microcontroller_repo_factory: Callable[[Session], MicrocontrollerRepository],
    ):
        self._repo_factory = repo_factory
        self._microcontroller_repo_factory = microcontroller_repo_factory
        self.logger = logger
        self.events = EventDispatcher(NatsPublisher(NATSClient()))

    # ---------------------------------------------------------------------
    # Repositories
    # ---------------------------------------------------------------------

    def _repo(self, db: Session) -> DeviceRepository:
        return self._repo_factory(db)

    def _microcontroller_repo(self, db: Session) -> MicrocontrollerRepository:
        return self._microcontroller_repo_factory(db)

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
                "Device does not belong to microcontroller | device_id=%s mc_id=%s",
                device.id,
                microcontroller_id,
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Device not found for the selected microcontroller",
            )

    def _ensure_threshold_for_auto(
        self,
        *,
        new_mode: DeviceMode | None,
        new_threshold: float | None,
        current_device: Device | None = None,
    ) -> None:
        effective_mode = new_mode or (current_device.mode if current_device else None)
        effective_threshold = (
            new_threshold
            if new_threshold is not None
            else (current_device.threshold_value if current_device else None)
        )

        if effective_mode == DeviceMode.AUTO_POWER and effective_threshold is None:
            self.logger.warning(
                "AUTO mode without threshold | device_id=%s",
                getattr(current_device, "id", None),
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="threshold_value is required when device mode is AUTO",
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
                order_by=repo.model.created_at.desc(),
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

            self._ensure_threshold_for_auto(
                new_mode=payload.get("mode"),
                new_threshold=payload.get("threshold_value"),
            )

            data = dict(payload)
            data["microcontroller_id"] = microcontroller.id

            device = repo.create(data)

            self.logger.info(
                "Device CREATED | device_id=%s mc_uuid=%s",
                device.id,
                microcontroller.uuid,
            )

            await self._publish_event(
                microcontroller_uuid=microcontroller.uuid,
                event_type=EventType.DEVICE_CREATED,
                payload=DeviceCreatedPayload(
                    device_id=device.id,
                    device_number=device.device_number,
                    mode=device.mode.value,
                    threshold_kw=device.threshold_value,
                ),
            )

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
            self._ensure_threshold_for_auto(
                new_mode=payload.get("mode"),
                new_threshold=payload.get("threshold_value"),
                current_device=device,
            )

            if microcontroller_id is not None:
                self._ensure_device_belongs_to_microcontroller(
                    device, microcontroller_id
                )

            updated = self._repo(db).update_for_user(device_id, user_id, payload)

            self.logger.info(
                "Device UPDATED | device_id=%s",
                updated.id,
            )

            await self._publish_event(
                microcontroller_uuid=device.microcontroller.uuid,
                event_type=EventType.DEVICE_UPDATED,
                payload=DeviceUpdatedPayload(
                    device_id=updated.id,
                    mode=updated.mode.value,
                    threshold_kw=updated.threshold_value,
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
                payload=DeviceDeletePayload(device_id=device.id),
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

        try:
            async with transactional_session(db):
                device.mode = "MANUAL"
                device.manual_state = state
                device.last_state_change_at = datetime.now(timezone.utc)

                await self._publish_event(
                    microcontroller_uuid=device.microcontroller.uuid,
                    event_type=EventType.DEVICE_COMMAND,
                    payload=DeviceCommandPayload(
                        device_id=device.id,
                        command="SET_STATE",
                        mode="MANUAL",
                        is_on=state,
                    ),
                )

                device_dto = DeviceResponse.model_validate(device, from_attributes=True)

            return device_dto, True

        except HTTPException:
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

    async def _publish_event(
        self, microcontroller_uuid: UUID, event_type: EventType, payload
    ) -> None:
        subject = subject_for_entity(microcontroller_uuid)
        self.logger.info("Subject: %s", subject)
        ack_subject = ack_subject_for_entity(microcontroller_uuid)
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
            await self.events.publish_event_and_wait_for_ack(
                entity_type="microcontroller",
                entity_id=str(microcontroller_uuid),
                event_type=event_type,
                data=payload,
                predicate=lambda e: self.ack_device_id(e) == payload.device_id,
                timeout=10.0,
                subject=subject,
                ack_subject=ack_subject,
            )

            self.logger.debug(
                "EVENT ACK received | type=%s mc_uuid=%s device_id=%s",
                event_type,
                microcontroller_uuid,
                payload.device_id,
            )

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
