from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import Field

from smart_common.schemas.base import APIModel, ORMModel


class ProviderBase(APIModel):
    name: str
    provider_type: str
    kind: str
    vendor: str | None
    unit: str
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    polling_interval_sec: int = Field(gt=0)
    enabled: bool = True


class ProviderCreate(ProviderBase):
    config: Dict[str, Any]
    login: str | None = None
    password: str | None = None


class ProviderUpdate(APIModel):
    name: Optional[str] = None
    provider_type: Optional[str] = None
    kind: Optional[str] = None
    vendor: Optional[str] = None
    unit: Optional[str] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    polling_interval_sec: Optional[int] = Field(None, gt=0)
    enabled: Optional[bool] = None
    config: Optional[Dict[str, Any]] = None
    login: Optional[str] = None
    password: Optional[str] = None


class ProviderOut(ProviderBase, ORMModel):
    id: int
    uuid: str
    installation_id: int
    last_value: Optional[float] = None
    last_measurement_at: Optional[datetime] = None
