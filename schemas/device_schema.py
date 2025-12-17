from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import Field

from enums.device import DeviceMode
from schemas.base import APIModel, ORMModel


class DeviceBase(APIModel):
    """Shared fields between create/update requests for a device."""

    name: str = Field(..., description="Friendly name of the device")
    mode: DeviceMode = Field(default=DeviceMode.MANUAL, description="Operation mode")
    device_number: Optional[int] = Field(
        None,
        ge=0,
        description="GPIO pin number assigned to the device",
    )
    provider_id: Optional[int] = Field(
        None,
        description="Optional provider that supplies AUTO decision data",
    )
    rated_power_w: Optional[float] = Field(
        None,
        gt=0,
        description="Declared device power in watts",
    )


class DeviceCreate(DeviceBase):
    microcontroller_id: int = Field(..., description="Microcontroller that controls this device")


class DeviceUpdate(APIModel):
    name: Optional[str] = None
    mode: Optional[DeviceMode] = None
    device_number: Optional[int] = Field(None, ge=0)
    provider_id: Optional[int] = None
    rated_power_w: Optional[float] = Field(None, gt=0)
    manual_state: Optional[bool] = None


class DeviceOut(DeviceBase, ORMModel):
    id: int
    uuid: UUID
    microcontroller_id: int
    manual_state: Optional[bool] = None
    last_state_change_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class DeviceList(ORMModel):
    devices: List[DeviceOut] = []
