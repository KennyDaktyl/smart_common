from __future__ import annotations

from typing import List, Optional

from pydantic import Field

from schemas.base import APIModel, ORMModel


class DeviceAutoConfigBase(APIModel):
    """Shared AUTO configuration attributes for devices."""

    provider_id: int = Field(..., description="Provider supplying AUTO data")
    comparison: str = Field(
        ..., regex=r"^[<>]=?$", description="Comparison operator used in AUTO rules"
    )
    threshold_value: float = Field(..., description="Threshold for AUTO evaluations")
    hysteresis_value: Optional[float] = Field(
        None, description="Optional hysteresis that prevents chattering"
    )
    enabled: bool = Field(True, description="Whether AUTO mode is enabled")


class DeviceAutoConfigCreate(DeviceAutoConfigBase):
    device_id: int = Field(..., description="Device linked to AUTO configuration")


class DeviceAutoConfigUpdate(APIModel):
    provider_id: Optional[int] = None
    comparison: Optional[str] = None
    threshold_value: Optional[float] = None
    hysteresis_value: Optional[float] = None
    enabled: Optional[bool] = None


class DeviceAutoConfigOut(DeviceAutoConfigBase, ORMModel):
    id: int
    device_id: int


class DeviceAutoConfigList(ORMModel):
    configs: List[DeviceAutoConfigOut] = []
