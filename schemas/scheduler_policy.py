from __future__ import annotations

from typing import Literal

from pydantic import Field, field_validator

from smart_common.enums.scheduler import (
    SchedulerControlMode,
    SchedulerPolicyEndBehavior,
    SchedulerPolicyType,
)
from smart_common.schemas.base import APIModel


class SchedulerControlPolicy(APIModel):
    policy_type: Literal[SchedulerPolicyType.TEMPERATURE_HYSTERESIS] = (
        SchedulerPolicyType.TEMPERATURE_HYSTERESIS
    )
    sensor_id: str = Field(min_length=1, max_length=128)
    target_temperature_c: float
    stop_above_target_delta_c: float = Field(default=0.0, ge=0)
    start_below_target_delta_c: float = Field(default=10.0, ge=0)
    heat_up_on_activate: bool = True
    end_behavior: SchedulerPolicyEndBehavior = (
        SchedulerPolicyEndBehavior.FORCE_OFF
    )

    @field_validator("sensor_id")
    @classmethod
    def normalize_sensor_id(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("sensor_id must not be empty")
        return normalized


def is_policy_control_mode(mode: SchedulerControlMode) -> bool:
    return mode == SchedulerControlMode.POLICY
