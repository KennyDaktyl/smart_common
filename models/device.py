# models/device.py
from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID as UUIDType
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from smart_common.core.db import Base
from smart_common.enums.device import DeviceMode


class Device(Base):
    __tablename__ = "devices"

    id: Mapped[int] = mapped_column(primary_key=True)
    uuid: Mapped[UUIDType] = mapped_column(
        UUID(as_uuid=True),
        unique=True,
        nullable=False,
        index=True,
        default=uuid4,
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    microcontroller_id: Mapped[int] = mapped_column(
        ForeignKey("microcontrollers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    scheduler_id: Mapped[int | None] = mapped_column(
        ForeignKey("schedulers.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    device_number: Mapped[int] = mapped_column(Integer, nullable=False)
    rated_power: Mapped[float | None] = mapped_column(Numeric(12, 4))
    mode: Mapped[DeviceMode] = mapped_column(
        Enum(DeviceMode, name="device_mode_enum"),
        default=DeviceMode.MANUAL,
        nullable=False,
    )
    manual_state: Mapped[bool | None] = mapped_column(Boolean)
    threshold_value: Mapped[float] = mapped_column(
        Numeric(12, 4),
        nullable=True,
        comment="Threshold value for the decision rule",
    )
    last_state_change_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    microcontroller = relationship(
        "Microcontroller",
        back_populates="devices",
    )
    scheduler = relationship(
        "Scheduler",
        back_populates="devices",
    )
    schedules = relationship(
        "DeviceSchedule",
        back_populates="device",
        cascade="all, delete-orphan",
    )
