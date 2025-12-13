from __future__ import annotations

from models.device_event import DeviceEvent

from .base import BaseRepository


class DeviceEventRepository(BaseRepository[DeviceEvent]):
    model = DeviceEvent
