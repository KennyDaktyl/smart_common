from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import Field

from schemas.base import APIModel, ORMModel


class ProviderPowerRecordBase(APIModel):
    provider_id: int = Field(..., description="Associated provider ID")
    current_power: Optional[float] = Field(None, description="Current measured power")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Timestamp of the sample"
    )


class ProviderPowerRecordCreate(ProviderPowerRecordBase):
    pass


class ProviderPowerRecordUpdate(APIModel):
    current_power: Optional[float] = None
    timestamp: Optional[datetime] = None


class ProviderPowerRecordOut(ProviderPowerRecordBase, ORMModel):
    id: int


class ProviderPowerRecordList(ORMModel):
    records: List[ProviderPowerRecordOut] = []
