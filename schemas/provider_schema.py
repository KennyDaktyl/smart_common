from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import ConfigDict, Field, field_validator

from smart_common.enums.unit import PowerUnit
from smart_common.providers.enums import ProviderKind, ProviderType, ProviderVendor
from smart_common.schemas.base import APIModel, ORMModel
from smart_common.schemas.provider_measurement_schemas import (
    ProviderMeasurementResponse,
)


class MicrocontrollerProviderConfig(APIModel):
    uuid: Optional[UUID] = Field(
        None,
        description="UUID of the provider",
    )
    external_id: str = ""

    @field_validator("uuid", mode="before")
    @classmethod
    def empty_string_to_none(cls, v):
        if v == "":
            return None
        return v


class ProviderBase(APIModel):

    uuid: UUID

    provider_type: ProviderType
    kind: ProviderKind
    vendor: Optional[ProviderVendor] = None

    unit: Optional[PowerUnit] = None

    value_min: Optional[float] = None
    value_max: Optional[float] = None

    enabled: bool = True

    config: Dict[str, Any] = Field(default_factory=dict)
    credentials: Optional[Dict[str, str]] = None


class ProviderCreateRequest(APIModel):
    name: str
    provider_type: ProviderType
    kind: ProviderKind
    vendor: ProviderVendor

    external_id: str | None = None
    unit: PowerUnit | None = None

    value_min: float | None = None
    value_max: float | None = None

    enabled: bool = True

    config: Dict[str, Any] | None = None
    credentials: Dict[str, str] | None = None

    wizard_session_id: str | None = None


class ProviderUpdateRequest(APIModel):
    name: Optional[str] = None
    vendor: Optional[ProviderVendor] = None
    unit: Optional[PowerUnit] = None

    value_min: Optional[float] = None
    value_max: Optional[float] = None

    enabled: Optional[bool] = None
    config: Optional[Dict[str, Any]] = None


class ProviderResponse(ORMModel):
    id: int
    uuid: UUID

    name: str
    provider_type: ProviderType
    kind: ProviderKind
    vendor: Optional[ProviderVendor]
    external_id: str | None
    unit: Optional[PowerUnit]

    value_min: Optional[float]
    value_max: Optional[float]

    default_expected_interval_sec: Optional[int]

    enabled: bool
    config: Dict[str, Any]

    created_at: datetime
    updated_at: datetime

    last_value: Optional[ProviderMeasurementResponse]

    model_config = ConfigDict(
        from_attributes=True,
        extra="forbid",
    )


class ProviderEnabledUpdateRequest(APIModel):
    enabled: bool


class ProviderCatalogItem(APIModel):
    name: str
    provider_type: ProviderType
    kind: ProviderKind | None = None
    vendor: ProviderVendor | None = None
    unit: PowerUnit | None = None
    enabled: bool | None = None
    uuid: UUID | None = None
    is_attached: bool | None = None
    is_virtual: bool = False
    description: str | None = None


class ProviderCatalogGroup(APIModel):
    type: ProviderType
    items: list[ProviderCatalogItem]


class ProviderCatalogResponse(APIModel):
    provider_groups: list[ProviderCatalogGroup]
