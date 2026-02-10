from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Any, List, Dict, Optional


class ProviderMeasurementResponse(BaseModel):
    id: int
    measured_at: datetime
    measured_value: Optional[float]
    measured_unit: Optional[str]
    metadata_payload: Dict[str, Any]

    model_config = ConfigDict(from_attributes=True)


class HourlyEnergyPoint(BaseModel):
    hour: datetime
    energy: float


class DayEnergyOut(BaseModel):
    date: str
    total_energy: float
    import_energy: float
    export_energy: float
    hours: List[HourlyEnergyPoint]


class ProviderEnergySeriesOut(BaseModel):
    unit: str
    days: Dict[str, DayEnergyOut]
