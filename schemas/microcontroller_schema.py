from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import Query
from pydantic import (
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
    computed_field,
    model_validator,
)

from smart_common.enums.device import DeviceMode
from smart_common.enums.microcontroller import MicrocontrollerType
from smart_common.enums.sensor import SensorType
from smart_common.enums.user import UserRole
from smart_common.models.provider import Provider
from smart_common.schemas.base import APIModel, ORMModel
from smart_common.schemas.device_schema import DeviceResponse
from smart_common.schemas.provider_schema import (
    MicrocontrollerProviderConfig,
    ProviderResponse,
)
from smart_common.schemas.pagination_schema import PaginationQuery


# =====================================================
# EMBEDDED
# =====================================================


class UserEmbeddedResponse(ORMModel):
    id: int
    email: EmailStr
    role: UserRole

    model_config = ConfigDict(from_attributes=True)


# =====================================================
# REQUESTS
# =====================================================


class MicrocontrollerCreateRequest(APIModel):
    name: str = Field(
        ...,
        description="Display name for the microcontroller",
        example="Gateway Alpha",
        min_length=1,
        max_length=100,
    )
    description: Optional[str] = None
    software_version: Optional[str] = None
    type: MicrocontrollerType = Field(MicrocontrollerType.RASPBERRY_PI_ZERO)
    max_devices: int = Field(4, gt=0)
    assigned_sensors: List[str] = Field(
        default_factory=list,
        example=[SensorType.DHT22.value, SensorType.BH1750.value],
    )


class MicrocontrollerUpdateRequest(APIModel):
    name: Optional[str] = None
    description: Optional[str] = None
    software_version: Optional[str] = None
    max_devices: Optional[int] = Field(None, gt=0)
    enabled: Optional[bool] = None
    assigned_sensors: Optional[List[str]] = None


class MicrocontrollerAdminUpdateRequest(MicrocontrollerUpdateRequest):
    user_id: Optional[int | None] = Field(
        None,
        description="Assign owner by user ID (null detaches user)",
    )


class MicrocontrollerStatusRequest(APIModel):
    enabled: bool


class MicrocontrollerPowerProviderRequest(APIModel):
    provider_uuid: Optional[UUID] = None


class MicrocontrollerAttachProviderRequest(APIModel):
    provider_id: Optional[UUID] = None


class MicrocontrollerSensorsUpdateRequest(APIModel):
    assigned_sensors: List[str]


# =====================================================
# CONFIG
# =====================================================


class DeviceConfig(APIModel):
    device_id: int
    device_uuid: Optional[UUID] = None
    device_number: Optional[int] = Field(None, ge=0)
    pin_number: Optional[int] = Field(None, ge=0)
    mode: DeviceMode
    rated_power: Optional[float] = None
    threshold_value: Optional[float] = None
    desired_state: Optional[bool] = None
    is_on: Optional[bool] = None

    @model_validator(mode="after")
    def normalize_device_number(self):
        number = self.device_number if self.device_number is not None else self.pin_number
        if number is None:
            raise ValueError("device_number or pin_number is required")
        self.device_number = number
        self.pin_number = number
        return self


class MicrocontrollerConfig(APIModel):
    uuid: Optional[UUID] = None
    device_max: int = Field(1, ge=1)
    active_low: bool = False
    devices_config: List[DeviceConfig] = Field(default_factory=list)
    provider: Optional[MicrocontrollerProviderConfig] = None

    @field_validator("uuid", mode="before")
    @classmethod
    def normalize_uuid(cls, v):
        if v in ("", "None", None):
            return None
        return v


class MicrocontrollerConfigUpdateRequest(APIModel):
    uuid: Optional[UUID] = None
    device_max: Optional[int] = Field(None, ge=1)
    active_low: Optional[bool] = None
    devices_config: Optional[List[DeviceConfig]] = None
    provider: Optional[MicrocontrollerProviderConfig] = None


# =====================================================
# RESPONSE
# =====================================================


class MicrocontrollerResponse(ORMModel):
    id: int
    uuid: UUID
    user_id: Optional[int]

    name: str
    description: Optional[str]
    software_version: Optional[str]
    type: MicrocontrollerType
    max_devices: int
    enabled: bool

    power_provider_id: Optional[int]

    devices: List[DeviceResponse] = Field(default_factory=list)
    assigned_sensors: List[str] = Field(default_factory=list)
    available_api_providers: List[ProviderResponse] = Field(default_factory=list)

    config: MicrocontrollerConfig
    created_at: datetime
    updated_at: datetime

    user: Optional[UserEmbeddedResponse] = None
    power_provider: Optional[ProviderResponse] = None

    @field_validator("config", mode="before")
    @classmethod
    def parse_config(cls, v):
        if isinstance(v, dict):
            return MicrocontrollerConfig(**v)
        return v

    model_config = ConfigDict(
        from_attributes=True,
        extra="forbid",
    )


class MicrocontrollerSensorsResponse(APIModel):
    assigned_sensors: List[str] = Field(
        default_factory=list,
        description="Physical sensors wired to this microcontroller",
        example=[SensorType.DHT22.value, SensorType.BH1750.value],
    )


class MicrocontrollerSetProviderRequest(APIModel):
    provider_uuid: UUID | None


# =====================================================
# QUERY
# =====================================================


class MicrocontrollerListQuery(PaginationQuery):
    search: str | None = Query(
        None,
        description="Search by microcontroller ID or UUID",
    )
