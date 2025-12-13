from __future__ import annotations

from models.device_schedule import DeviceSchedule

from .base import BaseRepository


class DeviceScheduleRepository(BaseRepository[DeviceSchedule]):
    model = DeviceSchedule
