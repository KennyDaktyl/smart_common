from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import and_

from smart_common.models.device_event import DeviceEvent

from .base import BaseRepository


class DeviceEventRepository(BaseRepository[DeviceEvent]):
    model = DeviceEvent

    def create_state_event(
        self,
        device_id: int,
        pin_state: bool,
        trigger_reason: str | None = None,
        power_kw: float | None = None,
        timestamp: datetime | None = None,
    ) -> DeviceEvent:
        event = DeviceEvent(
            device_id=device_id,
            state="ON" if pin_state else "OFF",
            pin_state=pin_state,
            trigger_reason=trigger_reason,
            power_kw=power_kw,
            timestamp=timestamp or datetime.now(timezone.utc),
        )
        self.session.add(event)
        self.session.commit()
        self.session.refresh(event)
        return event

    def list_for_device(
        self,
        device_id: int,
        limit: int,
        date_start: datetime,
        date_end: datetime,
    ) -> list[DeviceEvent]:
        return (
            self.session.query(self.model)
            .filter(
                and_(
                    self.model.device_id == device_id,
                    self.model.timestamp >= date_start,
                    self.model.timestamp <= date_end,
                )
            )
            .order_by(self.model.timestamp)
            .limit(limit)
            .all()
        )
