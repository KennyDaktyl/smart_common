from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.db import Base
from enums.device_event import DeviceEventName, DeviceEventType


class DeviceEvent(Base):
    """
    Records a Device-related event (state transitions, AUTO triggers, heartbeats,
    telemetry snapshots, and errors) for auditing or diagnostics.
    """

    __tablename__ = "device_events"

    id: Mapped[int] = mapped_column(primary_key=True)

    device_id: Mapped[int] = mapped_column(
        ForeignKey("devices.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # --- Event semantics ---
    event_type: Mapped[DeviceEventType] = mapped_column(
        Enum(DeviceEventType, name="device_event_type_enum"),
        nullable=False,
    )

    event_name: Mapped[DeviceEventName] = mapped_column(
        Enum(DeviceEventName, name="device_event_name_enum"),
        nullable=False,
    )

    # --- State snapshot ---
    device_state: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        comment="Logical state (e.g., ON/OFF)",
    )

    pin_state: Mapped[bool | None] = mapped_column(
        Boolean,
        nullable=True,
        comment="Physical GPIO/relay state",
    )

    # --- Telemetry snapshot ---
    measured_value: Mapped[float | None] = mapped_column(
        Numeric(12, 4),
        nullable=True,
        comment="Value reported by the provider (e.g., power, temperature)",
    )

    measured_unit: Mapped[str | None] = mapped_column(
        String(16),
        nullable=True,
        comment="Measurement unit (W, kW, C, %)",
    )

    # --- Context ---
    trigger_reason: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        comment="Reason why the event occurred",
    )

    source: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        comment="Source identifier (controller / agent / api)",
    )

    # --- Timestamp ---
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )

    # --- Relations ---
    device = relationship("Device")

    def __repr__(self) -> str:
        return (
            f"<DeviceEvent id={self.id} "
            f"device_id={self.device_id} "
            f"type={self.event_type} "
            f"name={self.event_name} "
            f"at={self.created_at}>"
        )
