from __future__ import annotations

from datetime import datetime
from typing import Optional, List

from smart_common.enums.device_event import DeviceEventName, DeviceEventType
from smart_common.schemas.base import APIModel, ORMModel


# ============
# REQUEST
# ============


class DeviceEventCreate(APIModel):
    device_id: int
    event_type: DeviceEventType = DeviceEventType.STATE
    event_name: DeviceEventName
    device_state: Optional[str] = None
    pin_state: Optional[bool] = None
    measured_value: Optional[float] = None
    measured_unit: Optional[str] = None
    trigger_reason: Optional[str] = None
    source: Optional[str] = None
    created_at: Optional[datetime] = None


# ============
# RESPONSE
# ============


class DeviceEventOut(ORMModel):
    id: int
    device_id: int
    event_type: DeviceEventType
    event_name: DeviceEventName
    device_state: Optional[str]
    pin_state: Optional[bool]
    measured_value: Optional[float]
    measured_unit: Optional[str]
    trigger_reason: Optional[str]
    source: Optional[str]
    created_at: datetime


class DeviceEventSeriesOut(APIModel):
    events: List[DeviceEventOut]
    total_minutes_on: int
    energy_kwh: Optional[float]
    rated_power_kw: Optional[float]
