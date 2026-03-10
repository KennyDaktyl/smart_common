from enum import Enum


class TelemetryChartType(str, Enum):
    LINE = "line"
    BAR = "bar"


class TelemetryAggregationMode(str, Enum):
    RAW = "raw"
    HOURLY_INTEGRAL = "hourly_integral"


class ProviderTelemetryCapability(str, Enum):
    POWER_METER = "power_meter"
    ENERGY_STORAGE = "energy_storage"
    THERMAL = "thermal"
