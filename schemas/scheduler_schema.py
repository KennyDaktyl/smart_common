from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import Field, model_validator

from smart_common.enums.scheduler import SchedulerControlMode, SchedulerDayOfWeek
from smart_common.schemas.automation_rule import (
    AutomationRuleGroup,
    build_legacy_power_rule,
    extract_legacy_power_threshold,
)
from smart_common.schemas.base import APIModel, ORMModel
from smart_common.schemas.device_dependency import DeviceDependencyRule
from smart_common.schemas.scheduler_policy import SchedulerControlPolicy

HHMM_PATTERN = r"^(?:[01]\d|2[0-3]):[0-5]\d$"
HHMM = Annotated[str, Field(pattern=HHMM_PATTERN)]
POWER_THRESHOLD_UNITS = {"W", "kW", "MW"}


def _to_minutes(value: str) -> int:
    parsed = datetime.strptime(value, "%H:%M")
    return parsed.hour * 60 + parsed.minute


def _validate_time_range(*, start_time: str, end_time: str, label: str) -> None:
    if _to_minutes(start_time) >= _to_minutes(end_time):
        raise ValueError(f"{label}: end_time must be later than start_time")


class SchedulerSlotIn(APIModel):
    day_of_week: SchedulerDayOfWeek
    start_local_time: HHMM | None = None
    end_local_time: HHMM | None = None
    start_utc_time: HHMM | None = None
    end_utc_time: HHMM | None = None
    start_time: HHMM | None = None
    end_time: HHMM | None = None
    use_power_threshold: bool = False
    power_threshold_value: float | None = Field(default=None, gt=0)
    power_threshold_unit: str | None = None
    activation_rule: AutomationRuleGroup | None = None
    control_mode: SchedulerControlMode = SchedulerControlMode.DIRECT
    control_policy: SchedulerControlPolicy | None = None
    device_dependency_rule: DeviceDependencyRule | None = None

    @model_validator(mode="after")
    def normalize_and_validate(self):
        start_time = self.start_time or self.start_utc_time
        end_time = self.end_time or self.end_utc_time
        if start_time is None or end_time is None:
            raise ValueError(
                "start_time/end_time or start_utc_time/end_utc_time must be provided"
            )

        self.start_time = start_time
        self.end_time = end_time
        self.start_utc_time = self.start_utc_time or start_time
        self.end_utc_time = self.end_utc_time or end_time
        self.start_local_time = self.start_local_time or start_time
        self.end_local_time = self.end_local_time or end_time

        _validate_time_range(
            start_time=self.start_time,
            end_time=self.end_time,
            label="start_time/end_time",
        )
        _validate_time_range(
            start_time=self.start_utc_time,
            end_time=self.end_utc_time,
            label="start_utc_time/end_utc_time",
        )
        _validate_time_range(
            start_time=self.start_local_time,
            end_time=self.end_local_time,
            label="start_local_time/end_local_time",
        )

        if self.use_power_threshold:
            if self.power_threshold_value is None:
                raise ValueError(
                    "power_threshold_value is required when use_power_threshold is true"
                )
            if self.power_threshold_unit is None:
                raise ValueError(
                    "power_threshold_unit is required when use_power_threshold is true"
                )
            if self.power_threshold_unit not in POWER_THRESHOLD_UNITS:
                raise ValueError(
                    f"power_threshold_unit must be one of: {', '.join(sorted(POWER_THRESHOLD_UNITS))}"
                )
            if self.activation_rule is None:
                self.activation_rule = build_legacy_power_rule(
                    value=self.power_threshold_value,
                    unit=self.power_threshold_unit,
                )
        elif self.activation_rule is None:
            self.power_threshold_value = None
            self.power_threshold_unit = None

        legacy_threshold = extract_legacy_power_threshold(self.activation_rule)
        if legacy_threshold is None:
            self.use_power_threshold = False
            self.power_threshold_value = None
            self.power_threshold_unit = None
        else:
            self.use_power_threshold = True
            self.power_threshold_value = legacy_threshold[0]
            self.power_threshold_unit = legacy_threshold[1]

        if self.control_mode == SchedulerControlMode.POLICY:
            if self.control_policy is None:
                raise ValueError(
                    "control_policy is required when control_mode is POLICY"
                )
        else:
            self.control_policy = None

        return self


class SchedulerCreateRequest(APIModel):
    name: str = Field(min_length=1, max_length=255)
    timezone: str = Field(default="UTC", min_length=1, max_length=64)
    utc_offset_minutes: int = Field(default=0, ge=-720, le=840)
    slots: list[SchedulerSlotIn] = Field(min_length=1)


class SchedulerUpdateRequest(SchedulerCreateRequest):
    pass


class SchedulerSlotResponse(ORMModel):
    day_of_week: SchedulerDayOfWeek
    start_time: str
    end_time: str
    start_local_time: str | None
    end_local_time: str | None
    start_utc_time: str | None
    end_utc_time: str | None
    use_power_threshold: bool
    power_threshold_value: float | None
    power_threshold_unit: str | None
    control_mode: SchedulerControlMode
    control_policy: SchedulerControlPolicy | None = Field(
        default=None,
        alias="control_policy_json",
    )
    device_dependency_rule: DeviceDependencyRule | None = Field(
        default=None,
        alias="device_dependency_rule_json",
    )
    activation_rule: AutomationRuleGroup | None = Field(
        default=None,
        alias="activation_rule_json",
    )


class SchedulerResponse(ORMModel):
    id: int
    uuid: UUID
    name: str
    timezone: str
    utc_offset_minutes: int
    slots: list[SchedulerSlotResponse]
    created_at: datetime
    updated_at: datetime


class SchedulerPowerThresholdProvider(APIModel):
    id: int
    uuid: UUID
    name: str
    unit: str


class SchedulerPowerThresholdUnitsResponse(APIModel):
    units: list[str]
    providers: list[SchedulerPowerThresholdProvider]
