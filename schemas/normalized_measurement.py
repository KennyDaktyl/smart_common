from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict

from smart_common.enums.provider_telemetry import (
    ProviderTelemetryCapability,
    TelemetryAggregationMode,
    TelemetryChartType,
)


@dataclass(frozen=True)
class NormalizedMetric:
    key: str
    value: float | None
    unit: str | None
    label: str
    chart_type: TelemetryChartType
    aggregation_mode: TelemetryAggregationMode
    capability_tag: ProviderTelemetryCapability | None = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class NormalizedMeasurement:
    provider_id: int
    value: float | None
    unit: str
    measured_at: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)
    extra_metrics: list[NormalizedMetric] = field(default_factory=list)
