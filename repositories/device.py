from __future__ import annotations

from models.device import Device

from .base import BaseRepository


class DeviceRepository(BaseRepository[Device]):
    model = Device
