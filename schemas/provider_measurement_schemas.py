from typing import List, Optional, Dict, Any
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ProviderMeasurementResponse(BaseModel):
    id: int
    measured_at: datetime
    measured_value: Optional[float]
    measured_unit: Optional[str]
    metadata_payload: Dict[str, Any]

    model_config = ConfigDict(from_attributes=True)


class ProviderMeasurementSeriesOut(BaseModel):
    measurements: list[ProviderMeasurementResponse]


class ProviderMeasurementSeriesOut(BaseModel):
    days: Dict[str, List[ProviderMeasurementResponse]]
