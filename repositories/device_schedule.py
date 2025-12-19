from __future__ import annotations

from smart_common.models.device_schedule import DeviceSchedule

from smart_common.repositories.base import BaseRepository


class DeviceScheduleRepository(BaseRepository[DeviceSchedule]):
    model = DeviceSchedule

    def list_for_device(self, device_id: int) -> list[DeviceSchedule]:
        return (
            self.session.query(self.model)
            .filter(self.model.device_id == device_id)
            .order_by(self.model.start_time)
            .all()
        )

    def update_schedule(self, schedule: DeviceSchedule, data: dict) -> DeviceSchedule:
        for attr, value in data.items():
            setattr(schedule, attr, value)
        self.session.flush()
        self.session.refresh(schedule)
        return schedule

    def delete_schedule(self, schedule: DeviceSchedule) -> None:
        self.session.delete(schedule)
        self.session.flush()
