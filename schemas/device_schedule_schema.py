from __future__ import annotations

from typing import List, Optional

from pydantic import Field

from schemas.base import APIModel, ORMModel


class DeviceScheduleBase(APIModel):
    """Common schedule attributes for both create and update payloads."""

    day_of_week: int = Field(..., ge=0, le=6, description="Day of week (0=Monday, 6=Sunday)")
    start_time: str = Field(..., regex=r"^\d{2}:\d{2}$", description="Start time in HH:MM format")
    end_time: str = Field(..., regex=r"^\d{2}:\d{2}$", description="End time in HH:MM format")
    enabled: bool = Field(True, description="Whether the schedule is active")


class DeviceScheduleCreate(DeviceScheduleBase):
    device_id: int = Field(..., description="Device the schedule applies to")


class DeviceScheduleUpdate(APIModel):
    day_of_week: Optional[int] = Field(None, ge=0, le=6)
    start_time: Optional[str] = Field(None, regex=r"^\d{2}:\d{2}$")
    end_time: Optional[str] = Field(None, regex=r"^\d{2}:\d{2}$")
    enabled: Optional[bool] = None


class DeviceScheduleOut(DeviceScheduleBase, ORMModel):
    id: int
    device_id: int


class DeviceScheduleList(ORMModel):
    schedules: List[DeviceScheduleOut] = []
