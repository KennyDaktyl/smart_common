from __future__ import annotations

from typing import List

from sqlalchemy import func

from smart_common.models.device import Device
from smart_common.models.microcontroller import Microcontroller
from smart_common.repositories.base import BaseRepository


class DeviceRepository(BaseRepository[Device]):
    model = Device
    default_order_by = Device.id.asc()

    def list_for_user(self, user_id: int) -> list[Device]:
        return (
            self.session.query(Device)
            .join(Device.microcontroller)
            .filter(Microcontroller.user_id == user_id)
            .order_by(Device.id.asc())
            .all()
        )

    def count_for_user(self, user_id: int) -> int:
        return (
            self.session.query(func.count(Device.id))
            .join(Device.microcontroller)
            .filter(Microcontroller.user_id == user_id)
            .scalar()
            or 0
        )

    def get_for_user_by_id(self, device_id: int, user_id: int) -> Device | None:
        return (
            self.session.query(self.model)
            .join(self.model.microcontroller)
            .filter(
                self.model.id == device_id,
                Microcontroller.user_id == user_id,
            )
            .first()
        )

    def get_for_microcontroller(
        self, microcontroller_id: int, user_id: int
    ) -> List[Device]:
        return (
            self.session.query(self.model)
            .join(self.model.microcontroller)
            .filter(
                self.model.microcontroller_id == microcontroller_id,
                Microcontroller.user_id == user_id,
            )
            .order_by(Device.id.asc())
            .all()
        )

    def create(self, payload: dict) -> Device:
        device = Device(**payload)
        self.session.add(device)
        self.session.flush()
        self.session.refresh(device)
        return device

    def update_for_user(
        self, device_id: int, user_id: int, data: dict
    ) -> Device | None:
        device = self.get_for_user_by_id(device_id, user_id)
        if not device:
            return None
        for key, value in data.items():
            setattr(device, key, value)
        self.session.flush()
        self.session.refresh(device)
        return device

    def count_for_microcontroller(self, microcontroller_id: int) -> int:
        return (
            self.session.query(func.count(self.model.id))
            .filter(self.model.microcontroller_id == microcontroller_id)
            .scalar()
        )

    def set_manual_state_for_user(
        self,
        *,
        device_id: int,
        user_id: int,
        state: bool,
    ) -> Device | None:
        device = self.get_for_user_by_id(device_id, user_id)
        if not device:
            return None

        device.manual_state = state
        self.session.commit()
        self.session.refresh(device)
        return device
