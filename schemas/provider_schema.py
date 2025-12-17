from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import Field

from enums.provider import ProviderKind, ProviderType, ProviderVendor
from enums.unit import PowerUnit
from schemas.base import APIModel, ORMModel


class ProviderBase(APIModel):
    """Common fields for provider payloads."""

    name: str = Field(..., description="User-visible provider name")
    provider_type: ProviderType
    kind: ProviderKind
    vendor: ProviderVendor | None = Field(None, description="Specific vendor")
    unit: PowerUnit | None = Field(None, description="Result unit for measurements")
    min_value: Optional[float] = Field(None, description="Minimum expected value")
    max_value: Optional[float] = Field(None, description="Maximum expected value")
    polling_interval_sec: int = Field(..., gt=0, description="Polling frequency in seconds")
    enabled: bool = Field(True, description="Whether the provider is active")


class ProviderCreate(ProviderBase):
    microcontroller_id: int = Field(..., description="Microcontroller that hosts the provider")
    config: Dict[str, Any] = Field(..., description="Provider-specific configuration")


class ProviderUpdate(APIModel):
    name: Optional[str] = None
    provider_type: Optional[ProviderType] = None
    kind: Optional[ProviderKind] = None
    vendor: Optional[ProviderVendor] = None
    unit: Optional[PowerUnit] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    polling_interval_sec: Optional[int] = Field(None, gt=0)
    enabled: Optional[bool] = None
    config: Optional[Dict[str, Any]] = None


class ProviderOut(ProviderBase, ORMModel):
    id: int
    uuid: UUID
    microcontroller_id: int
    last_value: Optional[float] = None
    last_measurement_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class ProviderList(ORMModel):
    providers: List[ProviderOut] = []
