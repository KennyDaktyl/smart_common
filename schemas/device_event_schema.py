from __future__ import annotations

from datetime import datetime
from typing import Optional, List

from pydantic import model_validator

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


class DeviceEventCreateFromAgent(APIModel):
    device_id: Optional[int] = None
    device_number: Optional[int] = None
    event_type: DeviceEventType = DeviceEventType.STATE
    event_name: DeviceEventName
    device_state: Optional[str] = None
    pin_state: Optional[bool] = None
    is_on: Optional[bool] = None
    measured_value: Optional[float] = None
    measured_unit: Optional[str] = None
    trigger_reason: Optional[str] = None
    source: Optional[str] = None
    created_at: Optional[datetime] = None

    @model_validator(mode="after")
    def validate_device_reference(self):
        if self.device_id is None and self.device_number is None:
            raise ValueError("device_id or device_number is required")
        return self


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
    energy: Optional[float]
    energy_unit: Optional[str]
    power_unit: Optional[str]
    rated_power: Optional[float]
