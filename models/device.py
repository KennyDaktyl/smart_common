# models/device.py
from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID as UUIDType
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.db import Base
from enums.device import DeviceMode


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

    # --- Core relations ---
    microcontroller_id: Mapped[int] = mapped_column(
        ForeignKey("microcontrollers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    provider_id: Mapped[int | None] = mapped_column(
        ForeignKey("providers.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # --- Hardware ---
    device_number: Mapped[int] = mapped_column(Integer, nullable=False)

    rated_power_w: Mapped[float | None] = mapped_column(Numeric(12, 4))

    # --- Control ---
    mode: Mapped[DeviceMode] = mapped_column(
        Enum(DeviceMode, name="device_mode_enum"),
        default=DeviceMode.MANUAL,
        nullable=False,
    )

    manual_state: Mapped[bool | None] = mapped_column(Boolean)

    last_state_change_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # --- Relations ---
    microcontroller = relationship(
        "Microcontroller",
        back_populates="devices",
    )

    provider = relationship("Provider")

    schedules = relationship(
        "DeviceSchedule",
        back_populates="device",
        cascade="all, delete-orphan",
    )

    auto_config = relationship(
        "DeviceAutoConfig",
        back_populates="device",
        uselist=False,
        cascade="all, delete-orphan",
    )
