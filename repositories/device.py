from __future__ import annotations

from typing import List

from smart_common.models.device import Device
from smart_common.models.installation import Installation
from smart_common.models.microcontroller import Microcontroller

from smart_common.repositories.base import BaseRepository


class DeviceRepository(BaseRepository[Device]):
    model = Device

    def list_for_user(self, user_id: int) -> List[Device]:
        return (
            self.session.query(self.model)
            .join(self.model.microcontroller)
            .join(Microcontroller.installation)
            .filter(Installation.user_id == user_id)
            .all()
        )

    def get_for_user_by_id(self, device_id: int, user_id: int) -> Device | None:
        return (
            self.session.query(self.model)
            .join(self.model.microcontroller)
            .join(Microcontroller.installation)
            .filter(
                self.model.id == device_id,
                Installation.user_id == user_id,
            )
            .first()
        )

    def get_for_raspberry(self, raspberry_id: int, user_id: int) -> List[Device]:
        return self.get_for_microcontroller(raspberry_id, user_id)

    def get_for_microcontroller(self, microcontroller_id: int, user_id: int) -> List[Device]:
        return (
            self.session.query(self.model)
            .join(self.model.microcontroller)
            .join(Microcontroller.installation)
            .filter(
                self.model.microcontroller_id == microcontroller_id,
                Installation.user_id == user_id,
            )
            .all()
        )

    def create(self, payload: dict) -> Device:
        device = Device(**payload)
        self.session.add(device)
        self.session.flush()
        self.session.refresh(device)
        return device

    def update_for_user(self, device_id: int, user_id: int, data: dict) -> Device | None:
        device = self.get_for_user_by_id(device_id, user_id)
        if not device:
            return None
        for key, value in data.items():
            setattr(device, key, value)
        self.session.flush()
        self.session.refresh(device)
        return device
