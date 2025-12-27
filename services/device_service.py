import logging
from typing import Callable
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from smart_common.core.db import transactional_session
from smart_common.enums.device import DeviceMode
from smart_common.enums.event import EventType
from smart_common.enums.user import UserRole
from smart_common.events.device_events import (
    DeviceUpdatedPayload,
)
from smart_common.events.event_dispatcher import EventDispatcher
from smart_common.models.device import Device
from smart_common.models.microcontroller import Microcontroller
from smart_common.nats.client import NATSClient
from smart_common.nats.publisher import NatsPublisher
from smart_common.repositories.device import DeviceRepository
from smart_common.repositories.microcontroller import MicrocontrollerRepository
from smart_common.schemas.device_schema import DeviceListQuery


logger = logging.getLogger(__name__)


class DeviceService:
    def __init__(
        self,
        repo_factory: Callable[[Session], DeviceRepository],
        microcontroller_repo_factory: Callable[[Session], MicrocontrollerRepository],
    ):
        self._repo_factory = repo_factory
        self._microcontroller_repo_factory = microcontroller_repo_factory
        self.logger = logging.getLogger(__name__)
        self.events = EventDispatcher(NatsPublisher(NATSClient()))

    # ---------------------------------------------------------------------
    # Repositories
    # ---------------------------------------------------------------------

    def _repo(self, db: Session) -> DeviceRepository:
        return self._repo_factory(db)

    def _microcontroller_repo(self, db: Session) -> MicrocontrollerRepository:
        return self._microcontroller_repo_factory(db)

    # ---------------------------------------------------------------------
    # Subjects
    # ---------------------------------------------------------------------

    def _subject_for_microcontroller(self, mc_uuid: UUID) -> str:
        return f"device_communication.microcontroller.{mc_uuid}.events"

    def _ack_subject(self, mc_uuid: UUID) -> str:
        return f"{self._subject_for_microcontroller(mc_uuid)}.ack"

    # ---------------------------------------------------------------------
    # Guards
    # ---------------------------------------------------------------------

    def _ensure_microcontroller(
        self, db: Session, user_id: int, mc_uuid: UUID
    ) -> Microcontroller:
        microcontroller = self._microcontroller_repo(db).get_for_user_by_uuid(
            mc_uuid, user_id
        )
        if not microcontroller:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Microcontroller not found",
            )
        return microcontroller

    def _ensure_device_belongs_to_microcontroller(
        self, device: Device, microcontroller_id: int
    ) -> None:
        if device.microcontroller_id != microcontroller_id:
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
        """
        Enforces rule:
        - AUTO mode requires threshold_value
        """
        effective_mode = new_mode or (current_device.mode if current_device else None)
        effective_threshold = (
            new_threshold
            if new_threshold is not None
            else (current_device.threshold_value if current_device else None)
        )

        if effective_mode == DeviceMode.AUTO_POWER and effective_threshold is None:
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

        return items, total

    def get_device(self, db: Session, device_id: int, user_id: int) -> Device:
        device = self._repo(db).get_for_user_by_id(device_id, user_id)
        if not device:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Device not found",
            )
        return device

    def list_for_microcontroller(
        self, db: Session, user_id: int, mc_uuid: UUID
    ) -> list[Device]:
        microcontroller = self._ensure_microcontroller(db, user_id, mc_uuid)
        return self._repo(db).get_for_microcontroller(microcontroller.id, user_id)

    # ---------------------------------------------------------------------
    # Commands
    # ---------------------------------------------------------------------

    async def create_device(
        self, db: Session, user_id: int, mc_uuid: UUID, payload: dict
    ) -> Device:
        microcontroller = self._ensure_microcontroller(db, user_id, mc_uuid)

        async with transactional_session(db):
            repo = self._repo(db)

            # ---- LIMIT GUARD ------------------------------------------------
            devices_count = repo.count_for_microcontroller(microcontroller.id)
            if devices_count >= microcontroller.max_devices:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        f"Microcontroller supports max "
                        f"{microcontroller.max_devices} devices"
                    ),
                )

            # ---- AUTO / THRESHOLD GUARD -------------------------------------
            self._ensure_threshold_for_auto(
                new_mode=payload.get("mode"),
                new_threshold=payload.get("threshold_value"),
            )

            data = dict(payload)
            data["microcontroller_id"] = microcontroller.id

            device = repo.create(data)

            self.logger.info(
                "Device created id=%s microcontroller=%s",
                device.id,
                microcontroller.uuid,
            )

            # Event intentionally commented out (as in original)
            # await self._publish_event(...)

            return device

    async def update_device(
        self,
        db: Session,
        user_id: int,
        device_id: int,
        payload: dict,
        microcontroller_id: int | None = None,
    ) -> Device:
        device = self.get_device(db, device_id, user_id)

        async with transactional_session(db):
            # ---- AUTO / THRESHOLD GUARD -------------------------------------
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

            if not updated:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Device not found",
                )

            self.logger.info("Device updated id=%s", updated.id)

            await self._publish_event(
                microcontroller_uuid=device.microcontroller.uuid,
                event_type=EventType.DEVICE_UPDATED,
                payload=DeviceUpdatedPayload(
                    device_id=updated.id,
                    mode=updated.mode.value,
                    threshold_kw=None,
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
        device = self.get_device(db, device_id, user_id)

        async with transactional_session(db):
            if microcontroller_id is not None:
                self._ensure_device_belongs_to_microcontroller(
                    device, microcontroller_id
                )

            # await self._publish_event(
            #     microcontroller_uuid=device.microcontroller.uuid,
            #     event_type=EventType.DEVICE_DELETED,
            #     payload=DeviceDeletePayload(device_id=device.id),
            # )

            self._repo(db).delete(device)
            self.logger.info("Device deleted id=%s", device.id)

    # ---------------------------------------------------------------------
    # Events
    # ---------------------------------------------------------------------

    async def _publish_event(
        self, microcontroller_uuid: UUID, event_type: EventType, payload
    ) -> None:
        subject = self._subject_for_microcontroller(microcontroller_uuid)
        ack_subject = self._ack_subject(microcontroller_uuid)

        try:
            await self.events.publish_event_and_wait_for_ack(
                subject=subject,
                ack_subject=ack_subject,
                event_type=event_type,
                payload=payload,
                predicate=lambda p: p.get("device_id") == payload.device_id,
                timeout=10.0,
            )
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail=(
                    f"Microcontroller did not acknowledge "
                    f"the {event_type.value} event: {exc}"
                ),
            ) from exc
