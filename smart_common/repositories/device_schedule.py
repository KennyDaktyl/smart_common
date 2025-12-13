from __future__ import annotations

from smart_common.models.device_schedule import DeviceSchedule

from .base import BaseRepository


class DeviceScheduleRepository(BaseRepository[DeviceSchedule]):
    model = DeviceSchedule
