from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from smart_common.enums.device import DeviceMode
from smart_common.schemas.base import APIModel, ORMModel


class DeviceListQuery(BaseModel):
    is_admin: bool = Field(
        default=False,
        description="If true and user is admin, returns all devices",
    )
    limit: int = Field(
        default=50,
        ge=1,
        le=100,
        description="Pagination limit (admin only)",
    )
    offset: int = Field(
        default=0,
        ge=0,
        description="Pagination offset (admin only)",
    )


class DeviceBase(APIModel):
    name: str = Field(
        ..., description="Friendly device name", example="Living Room Heater"
    )
    device_number: int = Field(..., ge=0, description="GPIO pin number", example=3)
    mode: DeviceMode = Field(
        DeviceMode.MANUAL,
        description="Operation mode",
        example=DeviceMode.MANUAL.value,
    )
    microcontroller_id: Optional[int] = Field(
        None,
        description="Microcontroller id",
        example=12,
    )
    rated_power: Optional[float] = Field(
        None,
        gt=0,
        description="Declared device power in watts",
        example=1200.0,
    )
    threshold_value: Optional[float] = Field(
        None,
        description="Threshold value for AUTO mode decision making",
        example=22.5,
    )

    @model_validator(mode="after")
    def validate_threshold_for_auto(self):
        if self.mode == DeviceMode.AUTO_POWER and self.threshold_value is None:
            raise ValueError("threshold_value is required when device mode is AUTO")
        return self


class DeviceCreateRequest(DeviceBase):
    pass


class DeviceUpdateRequest(APIModel):
    name: Optional[str] = None
    device_number: Optional[int] = Field(None, ge=0)
    mode: Optional[DeviceMode] = None
    provider_id: Optional[int] = None
    rated_power: Optional[float] = Field(None, gt=0)
    manual_state: Optional[bool] = None
    threshold_value: Optional[float] = None

    @model_validator(mode="after")
    def validate_threshold_for_auto(self):
        if self.mode == DeviceMode.AUTO_POWER and self.threshold_value is None:
            raise ValueError(
                "threshold_value must be provided when changing mode to AUTO"
            )
        return self


class DeviceResponse(ORMModel):
    id: int
    uuid: UUID
    microcontroller_id: int
    name: str
    device_number: int
    mode: DeviceMode
    rated_power: Optional[float]
    threshold_value: Optional[float]
    manual_state: Optional[bool]
    last_state_change_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime


class DeviceSetManualStateRequest(APIModel):
    state: bool


class DeviceManualStateResponse(APIModel):
    status: str
    message: str | None = None
    device: DeviceResponse
