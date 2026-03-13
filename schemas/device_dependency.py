from __future__ import annotations

from pydantic import Field, model_validator

from smart_common.enums.device_dependency import DeviceDependencyAction
from smart_common.schemas.base import APIModel


class DeviceDependencyRule(APIModel):
    target_device_id: int = Field(ge=1)
    target_device_number: int | None = Field(default=None, ge=1)
    when_source_on: DeviceDependencyAction = DeviceDependencyAction.NONE
    when_source_off: DeviceDependencyAction = DeviceDependencyAction.NONE

    @model_validator(mode="after")
    def normalize_noop_rule(self):
        if (
            self.when_source_on == DeviceDependencyAction.NONE
            and self.when_source_off == DeviceDependencyAction.NONE
        ):
            self.target_device_number = None
        return self


def parse_device_dependency_rule(
    value: DeviceDependencyRule | dict | None,
) -> DeviceDependencyRule | None:
    if isinstance(value, DeviceDependencyRule):
        return value
    if isinstance(value, dict):
        try:
            return DeviceDependencyRule.model_validate(value)
        except Exception:
            return None
    return None
