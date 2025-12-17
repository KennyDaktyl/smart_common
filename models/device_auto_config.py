from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.db import Base


class DeviceAutoConfig(Base):
    """
    AUTO mode configuration for a Device. Represents a strict one-to-one link that
    enables automatic decisions when populated.
    """

    __tablename__ = "device_auto_configs"

    id: Mapped[int] = mapped_column(primary_key=True)

    device_id: Mapped[int] = mapped_column(
        ForeignKey("devices.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )

    provider_id: Mapped[int] = mapped_column(
        ForeignKey("providers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Decision data source (API / SENSOR / VIRTUAL)",
    )

    # --- Decision rule ---
    comparison: Mapped[str] = mapped_column(
        String(4),
        nullable=False,
        default=">",
        comment="Comparison operator: >, <, >=, <=",
    )

    threshold_value: Mapped[float] = mapped_column(
        Numeric(12, 4),
        nullable=False,
        comment="Threshold value for the decision rule",
    )

    hysteresis_value: Mapped[float | None] = mapped_column(
        Numeric(12, 4),
        nullable=True,
        comment="Hysteresis offset (optional)",
    )

    enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        comment="Whether AUTO mode is enabled",
    )

    # --- Relations ---
    device = relationship(
        "Device",
        back_populates="auto_config",
    )

    provider = relationship("Provider")

    def __repr__(self) -> str:
        return (
            f"<DeviceAutoConfig device_id={self.device_id} "
            f"provider_id={self.provider_id} "
            f"{self.comparison}{self.threshold_value}>"
        )
