import logging
from datetime import datetime, timezone
from typing import Callable

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from smart_common.enums.device_event import DeviceEventType
from smart_common.models.device import Device
from smart_common.repositories.device import DeviceRepository
from smart_common.repositories.device_event import DeviceEventRepository
from smart_common.schemas.device_event_schema import DeviceEventOut


class DeviceEventService:
    def __init__(
        self,
        event_repo_factory: Callable[[Session], DeviceEventRepository],
        device_repo_factory: Callable[[Session], DeviceRepository],
    ):
        self._event_repo_factory = event_repo_factory
        self._device_repo_factory = device_repo_factory
        self.logger = logging.getLogger(__name__)

    def _event_repo(self, db: Session) -> DeviceEventRepository:
        return self._event_repo_factory(db)

    def _device_repo(self, db: Session) -> DeviceRepository:
        return self._device_repo_factory(db)

    def _get_device(self, db: Session, user_id: int, device_id: int) -> Device:
        device = self._device_repo(db).get_for_user_by_id(device_id, user_id)
        if not device:
            raise HTTPException(status_code=404, detail="Device not found")
        return device

    def list_device_events(
        self,
        *,
        db: Session,
        user_id: int,
        device_id: int,
        limit: int,
        date_start: datetime | None,
        date_end: datetime | None,
        event_type: DeviceEventType | None = None,
    ) -> dict:
        device = self._get_device(db, user_id, device_id)

        now = datetime.now(timezone.utc)
        start = date_start or now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = date_end or now

        events = self._event_repo(db).list_for_device(
            device_id=device.id,
            limit=limit,
            date_start=start,
            date_end=end,
            event_type=event_type,
        )

        schema_events = [DeviceEventOut.model_validate(e) for e in events]

        rated_power_kw = (
            float(device.rated_power_w) / 1000 if device.rated_power_w else None
        )

        total_seconds_on = 0.0
        energy_kwh = 0.0

        for idx, event in enumerate(schema_events):
            current_ts = event.created_at
            next_ts = (
                schema_events[idx + 1].created_at
                if idx + 1 < len(schema_events)
                else end
            )

            if event.pin_state:
                seconds = max(0, (next_ts - current_ts).total_seconds())
                total_seconds_on += seconds
                power_kw = (
                    rated_power_kw
                    if rated_power_kw is not None
                    else (event.measured_value or 0.0)
                )
                energy_kwh += power_kw * (seconds / 3600)

        return {
            "events": schema_events,
            "total_minutes_on": int(total_seconds_on // 60),
            "energy_kwh": round(energy_kwh, 3) if energy_kwh else None,
            "rated_power_kw": rated_power_kw,
        }
