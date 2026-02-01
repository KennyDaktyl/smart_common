from __future__ import annotations

from datetime import datetime, timezone
from sqlalchemy import and_

from smart_common.enums.device_event import DeviceEventName, DeviceEventType
from smart_common.models.device_event import DeviceEvent
from smart_common.repositories.base import BaseRepository


class DeviceEventRepository(BaseRepository[DeviceEvent]):
    model = DeviceEvent

    def create(
        self,
        *,
        device_id: int,
        event_type: DeviceEventType,
        event_name: DeviceEventName,
        device_state: str | None = None,
        pin_state: bool | None = None,
        measured_value: float | None = None,
        measured_unit: str | None = None,
        trigger_reason: str | None = None,
        source: str | None = None,
        created_at: datetime | None = None,
    ) -> DeviceEvent:
        event = DeviceEvent(
            device_id=device_id,
            event_type=event_type,
            event_name=event_name,
            device_state=device_state,
            pin_state=pin_state,
            measured_value=measured_value,
            measured_unit=measured_unit,
            trigger_reason=trigger_reason,
            source=source,
            created_at=created_at or datetime.now(timezone.utc),
        )
        self.session.add(event)
        self.session.commit()
        self.session.refresh(event)
        return event

    def list_for_device(
        self,
        *,
        device_id: int,
        limit: int,
        date_start: datetime,
        date_end: datetime,
        event_type: DeviceEventType | None = None,
    ) -> list[DeviceEvent]:
        filters = [
            self.model.device_id == device_id,
            self.model.created_at >= date_start,
            self.model.created_at <= date_end,
        ]
        if event_type:
            filters.append(self.model.event_type == event_type)

        return (
            self.session.query(self.model)
            .filter(and_(*filters))
            .order_by(self.model.created_at)
            .limit(limit)
            .all()
        )
