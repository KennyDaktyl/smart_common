from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import Field, field_validator

from smart_common.enums.scheduler import SchedulerDayOfWeek
from smart_common.schemas.base import APIModel, ORMModel

HHMM_PATTERN = r"^(?:[01]\d|2[0-3]):[0-5]\d$"
HHMM = Annotated[str, Field(pattern=HHMM_PATTERN)]


def _to_minutes(value: str) -> int:
    parsed = datetime.strptime(value, "%H:%M")
    return parsed.hour * 60 + parsed.minute


class SchedulerSlotIn(APIModel):
    day_of_week: SchedulerDayOfWeek
    start_time: HHMM
    end_time: HHMM

    @field_validator("end_time")
    @classmethod
    def validate_time_range(cls, end_time: str, info):
        start_time = info.data.get("start_time")
        if start_time and _to_minutes(start_time) >= _to_minutes(end_time):
            raise ValueError("end_time must be later than start_time")
        return end_time


class SchedulerCreateRequest(APIModel):
    name: str = Field(min_length=1, max_length=255)
    slots: list[SchedulerSlotIn] = Field(min_length=1)


class SchedulerUpdateRequest(SchedulerCreateRequest):
    pass


class SchedulerSlotResponse(ORMModel):
    day_of_week: SchedulerDayOfWeek
    start_time: str
    end_time: str


class SchedulerResponse(ORMModel):
    id: int
    uuid: UUID
    name: str
    slots: list[SchedulerSlotResponse]
    created_at: datetime
    updated_at: datetime
