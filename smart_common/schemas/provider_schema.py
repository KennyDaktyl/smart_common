from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import Field

from smart_common.enums.provider import (
    PowerUnit,
    ProviderKind,
    ProviderType,
    ProviderVendor,
)
from smart_common.schemas.base import APIModel, ORMModel


class ProviderBase(APIModel):
    name: str
    provider_type: ProviderType
    kind: ProviderKind
    vendor: ProviderVendor | None
    unit: PowerUnit
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    polling_interval_sec: int = Field(gt=0)
    enabled: bool = True


class ProviderCreate(ProviderBase):
    installation_id: int
    config: Dict[str, Any]


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
    installation_id: int
    last_value: Optional[float] = None
    last_measurement_at: Optional[datetime] = None
