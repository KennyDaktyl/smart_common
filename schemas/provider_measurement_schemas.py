from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


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


class EnergyEntryPoint(BaseModel):
    timestamp: datetime
    energy: float


class PowerEntryPoint(BaseModel):
    timestamp: datetime
    power: float


class DayEnergyOut(BaseModel):
    date: str
    total_energy: float
    import_energy: float
    export_energy: float
    hours: List[HourlyEnergyPoint]
    entries: List[ProviderMeasurementResponse]


class DayPowerOut(BaseModel):
    date: str
    entries: List[PowerEntryPoint]


class ProviderEnergySeriesOut(BaseModel):
    unit: str
    days: Dict[str, DayEnergyOut]


class ProviderPowerSeriesOut(BaseModel):
    unit: Optional[str]
    days: Dict[str, DayPowerOut]


class ProviderCurrentHourPoolOut(BaseModel):
    provider_uuid: UUID
    hour_start: datetime
    as_of: datetime
    unit: str
    current_power: Optional[float]
    current_power_unit: Optional[str]
    production_energy: float
    device_consumption_energy: float
    net_energy: float
    available_energy: float
    provider_includes_device_consumption: bool
    devices_considered: int
