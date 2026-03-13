from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from smart_common.enums.provider_telemetry import (
    ProviderTelemetryCapability,
    TelemetryAggregationMode,
    TelemetryChartType,
)


class ProviderMeasurementResponse(BaseModel):
    id: int
    measured_at: datetime
    measured_value: Optional[float]
    measured_unit: Optional[str]
    metadata_payload: Dict[str, Any]
    extra_data: Dict[str, Any]

    model_config = ConfigDict(from_attributes=True)


class ProviderTelemetryMetricDefinition(BaseModel):
    metric_key: str
    label: str
    unit: Optional[str]
    chart_type: TelemetryChartType
    aggregation_mode: TelemetryAggregationMode
    capability_tag: ProviderTelemetryCapability | None = None

    model_config = ConfigDict(from_attributes=True)


class HourlyEnergyPoint(BaseModel):
    hour: datetime
    energy: float
    revenue: float | None = None


class HourlyRevenuePoint(BaseModel):
    hour: datetime
    revenue: float
    export_energy: float


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


class ProviderMetricPoint(BaseModel):
    timestamp: datetime
    value: float


class ProviderMetricHourlyPoint(BaseModel):
    hour: datetime
    value: float


class ProviderMetricSeriesOut(BaseModel):
    metric_key: str
    label: str
    unit: Optional[str]
    source_unit: Optional[str] = None
    chart_type: TelemetryChartType
    aggregation_mode: TelemetryAggregationMode
    capability_tag: ProviderTelemetryCapability | None = None
    date: str
    entries: List[ProviderMetricPoint] = []
    hours: List[ProviderMetricHourlyPoint] = []


class MarketEnergyPricePointOut(BaseModel):
    interval_start: datetime
    interval_end: datetime
    price: float
    currency: str
    unit: str


class ProviderMarketPriceOut(BaseModel):
    market: str
    label: str
    price: float
    currency: str
    unit: str
    interval_start: datetime
    interval_end: datetime
    source_updated_at: datetime | None = None
    price_per_energy_unit: float | None = None
    energy_unit: str | None = None
    history: List[MarketEnergyPricePointOut] = []


class ProviderMatchedRevenueOut(BaseModel):
    market: str
    label: str
    currency: str
    energy_unit: str | None = None
    total_export_energy: float = 0.0
    total_revenue: float = 0.0
    matched_intervals: int = 0
    hours: List[HourlyRevenuePoint] = []
