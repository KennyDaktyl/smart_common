import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Callable

from fastapi import HTTPException
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

    def _to_utc_aware(self, dt: datetime) -> datetime:
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)

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

        start = (
            self._to_utc_aware(date_start)
            if date_start
            else now.replace(hour=0, minute=0, second=0, microsecond=0)
        )
        end = self._to_utc_aware(date_end) if date_end else now

        events = self._event_repo(db).list_for_device(
            device_id=device.id,
            limit=limit,
            date_start=start,
            date_end=end,
            event_type=event_type,
        )

        schema_events = [
            DeviceEventOut.model_validate(e, from_attributes=True) for e in events
        ]

        total_seconds_on = 0.0
        energy = Decimal("0")

        if device.rated_power is None:
            energy_unit = None
        else:
            rated_power = Decimal(device.rated_power)  # zakładamy że to kW
            energy_unit = "kWh"

            for idx, event in enumerate(schema_events):
                current_ts = self._to_utc_aware(event.created_at)

                next_ts = (
                    self._to_utc_aware(schema_events[idx + 1].created_at)
                    if idx + 1 < len(schema_events)
                    else end
                )

                if event.pin_state:
                    seconds = max(0, (next_ts - current_ts).total_seconds())
                    total_seconds_on += seconds

                    hours = Decimal(str(seconds)) / Decimal("3600")
                    energy += rated_power * hours

        return {
            "events": schema_events,
            "total_minutes_on": int(total_seconds_on // 60),
            "energy": round(float(energy), 3) if energy > 0 else None,
            "energy_unit": energy_unit,
            "power_unit": "kW" if device.rated_power else None,
            "rated_power": (float(device.rated_power) if device.rated_power else None),
        }
