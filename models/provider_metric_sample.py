from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import Mapped, mapped_column, relationship

from smart_common.core.db import Base


class ProviderMetricSample(Base):
    __tablename__ = "provider_metric_samples"
    __table_args__ = (
        UniqueConstraint(
            "provider_measurement_id",
            "metric_key",
            name="uq_provider_metric_samples_measurement_metric_key",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    provider_id: Mapped[int] = mapped_column(
        ForeignKey("providers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    provider_measurement_id: Mapped[int] = mapped_column(
        ForeignKey("provider_measurements.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    metric_key: Mapped[str] = mapped_column(String(length=64), nullable=False)
    measured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    value: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False)
    unit: Mapped[str | None] = mapped_column(String(length=16), nullable=True)
    metadata_payload: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        MutableDict.as_mutable(JSON),
        nullable=False,
        default=dict,
    )

    provider = relationship("Provider", back_populates="metric_samples")
    provider_measurement = relationship(
        "ProviderMeasurement",
        back_populates="metric_samples",
    )
