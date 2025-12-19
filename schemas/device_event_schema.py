from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import Field

from smart_common.enums.device_event import DeviceEventName, DeviceEventType
from smart_common.schemas.base import APIModel, ORMModel


class DeviceEventBase(APIModel):
    """Shared payload for device events."""

    event_type: DeviceEventType
    event_name: DeviceEventName
    device_state: Optional[str] = Field(None, description="Logical device state")
    pin_state: Optional[bool] = Field(None, description="Physical GPIO or relay state")
    measured_value: Optional[float] = Field(None, description="Value captured during the event")
    measured_unit: Optional[str] = Field(None, description="Unit of measured_value")
    trigger_reason: Optional[str] = Field(None, description="Why the event fired")
    source: Optional[str] = Field(None, description="Origin of the event")


class DeviceEventCreate(DeviceEventBase):
    device_id: int = Field(..., description="Device that generated the event")
    created_at: Optional[datetime] = Field(None, description="Event timestamp")


class DeviceEventUpdate(APIModel):
    event_type: Optional[DeviceEventType] = None
    event_name: Optional[DeviceEventName] = None
    device_state: Optional[str] = None
    pin_state: Optional[bool] = None
    measured_value: Optional[float] = None
    measured_unit: Optional[str] = None
    trigger_reason: Optional[str] = None
    source: Optional[str] = None


class DeviceEventOut(DeviceEventBase, ORMModel):
    id: int
    device_id: int
    created_at: datetime


class DeviceEventList(ORMModel):
    events: List[DeviceEventOut] = []
