from __future__ import annotations

from smart_common.models.device import Device

from .base import BaseRepository


class DeviceRepository(BaseRepository[Device]):
    model = Device
