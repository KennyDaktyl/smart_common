from __future__ import annotations

from sqlalchemy import Enum, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from smart_common.core.db import Base
from smart_common.enums.provider_telemetry import (
    ProviderTelemetryCapability,
    TelemetryAggregationMode,
    TelemetryChartType,
)


def _enum_values(enum_cls):
    return [item.value for item in enum_cls]


class ProviderMetricDefinition(Base):
    __tablename__ = "provider_metric_definitions"
    __table_args__ = (
        UniqueConstraint(
            "provider_id",
            "metric_key",
            name="uq_provider_metric_definitions_provider_metric_key",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    provider_id: Mapped[int] = mapped_column(
        ForeignKey("providers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    metric_key: Mapped[str] = mapped_column(String(length=64), nullable=False)
    label: Mapped[str] = mapped_column(String(length=128), nullable=False)
    unit: Mapped[str | None] = mapped_column(String(length=16), nullable=True)
    chart_type: Mapped[TelemetryChartType] = mapped_column(
        Enum(
            TelemetryChartType,
            name="telemetry_chart_type_enum",
            values_callable=_enum_values,
        ),
        nullable=False,
    )
    aggregation_mode: Mapped[TelemetryAggregationMode] = mapped_column(
        Enum(
            TelemetryAggregationMode,
            name="telemetry_aggregation_mode_enum",
            values_callable=_enum_values,
        ),
        nullable=False,
    )
    capability_tag: Mapped[ProviderTelemetryCapability | None] = mapped_column(
        Enum(
            ProviderTelemetryCapability,
            name="provider_telemetry_capability_enum",
            values_callable=_enum_values,
        ),
        nullable=True,
    )

    provider = relationship("Provider", back_populates="telemetry_metrics")
