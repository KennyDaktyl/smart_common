from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import Query
from pydantic import ConfigDict, EmailStr, Field, field_validator

from smart_common.enums.device import DeviceMode
from smart_common.enums.microcontroller import MicrocontrollerType
from smart_common.enums.sensor import SensorType
from smart_common.enums.user import UserRole
from smart_common.schemas.base import APIModel, ORMModel
from smart_common.schemas.device_schema import DeviceResponse
from smart_common.schemas.provider_schema import (
    MicrocontrollerProviderConfig,
    ProviderResponse,
)
from smart_common.schemas.pagination_schema import PaginationQuery


class UserEmbeddedResponse(ORMModel):
    id: int
    email: EmailStr
    role: UserRole

    model_config = ConfigDict(from_attributes=True)


class MicrocontrollerCreateRequest(APIModel):
    user_id: Optional[int] = Field(
        None,
        description="ID of the user who will own this microcontroller (admin only)",
        example=42,
    )
    name: str = Field(
        ...,
        description="Display name for the microcontroller",
        example="Gateway Alpha",
        min_length=1,
        max_length=100,
    )
    description: Optional[str] = Field(
        None,
        description="Additional notes or location details",
        example="Installed on rooftop, north side",
    )
    software_version: Optional[str] = Field(
        None,
        description="Firmware version running on the controller",
        example="1.4.2",
    )
    type: MicrocontrollerType = Field(
        MicrocontrollerType.RASPBERRY_PI_ZERO,
        description="Hardware type of the microcontroller",
        example=MicrocontrollerType.RASPBERRY_PI_ZERO.value,
    )
    max_devices: int = Field(
        4,
        gt=0,
        description="Maximum number of devices that can be attached",
        example=4,
    )
    assigned_sensors: List[str] = Field(
        default_factory=list,
        description="Physical sensors wired to this microcontroller (sensor code strings)",
        example=[SensorType.DHT22.value, SensorType.BH1750.value],
    )


class MicrocontrollerUpdateRequest(MicrocontrollerCreateRequest):
    enabled: Optional[bool] = Field(
        None,
        description="True to allow communication, false to pause the controller",
        example=True,
    )


class MicrocontrollerAdminUpdateRequest(APIModel):
    user_id: Optional[int | None] = Field(
        None,
        description="Assign owner by user ID (null detaches user)",
        example=42,
    )
    name: Optional[str] = Field(None)
    description: Optional[str] = Field(None)
    software_version: Optional[str] = Field(None)
    max_devices: Optional[int] = Field(None, gt=0)
    enabled: Optional[bool] = Field(None)

    assigned_sensors: Optional[List[str]] = Field(
        None,
        description="Replace assigned sensors (admin only)",
        example=[SensorType.DHT22.value, SensorType.BME280.value],
    )


class MicrocontrollerStatusRequest(APIModel):
    enabled: bool = Field(
        ...,
        description="True to allow communication, false to pause the controller",
        example=True,
    )


class MicrocontrollerPowerProviderRequest(APIModel):
    provider_uuid: Optional[UUID] = Field(
        None,
        description="Selected API power provider UUID (null detaches the provider)",
    )


class MicrocontrollerAttachProviderRequest(APIModel):
    provider_id: Optional[UUID] = Field(
        None,
        description="Provider UUID to attach (null detaches and falls back to manual/scheduled)",
    )


class MicrocontrollerSensorsResponse(APIModel):
    assigned_sensors: List[str] = Field(
        default_factory=list,
        description="Physical sensors wired to this microcontroller",
        example=[SensorType.DHT22.value, SensorType.BH1750.value],
    )


class MicrocontrollerSensorsUpdateRequest(APIModel):
    assigned_sensors: List[str] = Field(
        ...,
        description="Replace assigned sensors for this microcontroller (empty list clears hardware assignments)",
        example=[SensorType.DHT22.value, SensorType.BME280.value],
    )


class DeviceConfig(APIModel):
    device_id: int = Field(
        ..., description="ID of the device attached to the microcontroller"
    )
    pin_number: int = Field(..., ge=0, description="GPIO pin number used by the device")
    mode: DeviceMode = Field(
        ..., description="Mode of the device (e.g., input, output)"
    )
    threshold_value: Optional[float] = Field(
        None, description="Threshold value for the device (if applicable)"
    )
    is_on: Optional[bool] = Field(
        None, description="Current state of the device (if applicable)"
    )


class MicrocontrollerConfig(APIModel):
    uuid: Optional[UUID] = Field(
        None,
        description="Microcontroller UUID visible to device firmware",
    )
    device_max: int = Field(
        1,
        ge=1,
        description="Maximum number of devices supported by firmware",
    )
    active_low: bool = Field(
        False,
        description="Whether GPIO pins are active-low",
    )
    devices_config: List[DeviceConfig] = Field(
        default_factory=list,
        description="Devices configuration attached to the microcontroller",
    )
    provider: Optional[MicrocontrollerProviderConfig] = None

    @field_validator("uuid", mode="before")
    @classmethod
    def normalize_uuid(cls, v):
        if v in ("None", "", None):
            return None
        return v


class MicrocontrollerConfigUpdateRequest(APIModel):
    uuid: Optional[UUID] = None
    device_max: Optional[int] = Field(None, ge=1)
    active_low: Optional[bool] = None
    devices_config: Optional[list[int]] = None
    provider: Optional[MicrocontrollerProviderConfig] = None


class MicrocontrollerResponse(ORMModel):
    id: int
    uuid: UUID
    user_id: Optional[int]

    # ---- DEPRECATED (frontend backward compat) ----
    sensor_providers: Optional[List[ProviderResponse]] = Field(default=None)
    power_provider: Optional[ProviderResponse] = Field(default=None)

    # ---- CURRENT CONTRACT ----
    active_provider: Optional[ProviderResponse] = Field(
        None,
        description="Currently attached provider (API or sensor-derived)",
    )

    available_sensor_providers: List[ProviderResponse] = Field(
        default_factory=list,
        description="Providers derived from assigned physical sensors",
    )

    available_api_providers: List[ProviderResponse] = Field(
        default_factory=list,
        description="API providers available for this user",
    )

    devices: List[DeviceResponse] = Field(default_factory=list)

    # ---- META ----
    name: str
    description: Optional[str]
    software_version: Optional[str]
    type: MicrocontrollerType
    max_devices: int

    assigned_sensors: List[str] = Field(default_factory=list)
    config: MicrocontrollerConfig
    enabled: bool
    created_at: datetime
    updated_at: datetime

    # ---- ADMIN ONLY ----
    user_email: Optional[str] = Field(
        None,
        description="Owner email (admin views only)",
    )
    user: Optional[UserEmbeddedResponse] = Field(
        None,
        description="Owner details (admin views only)",
    )
    model_config = ConfigDict(
        from_attributes=True,
        extra="forbid",
    )


class MicrocontrollerListQuery(PaginationQuery):
    search: str | None = Query(
        None,
        description="Search by microcontroller ID or UUID",
        example="1 or 550e8400-e29b-41d4-a716-446655440000",
    )
