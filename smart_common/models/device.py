import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import JSON, UUID, Boolean, DateTime, Enum, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from smart_common.core.db import Base
from smart_common.enums.device import DeviceMode


class Device(Base):
    __tablename__ = "devices"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(nullable=False)
    uuid: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), unique=True, default=uuid.uuid4, index=True)

    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    raspberry_id: Mapped[int] = mapped_column(Integer, ForeignKey("raspberries.id", ondelete="CASCADE"))

    device_number: Mapped[int] = mapped_column(Integer, nullable=False)
    rated_power_kw: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)

    mode: Mapped[DeviceMode] = mapped_column(
        Enum(DeviceMode, name="devicemode", create_type=False),
        default=DeviceMode.MANUAL,
        nullable=False,
    )

    threshold_kw: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    hysteresis_w: Mapped[Decimal] = mapped_column(Numeric(12, 4), default=100)

    schedule: Mapped[JSON | None] = mapped_column(JSON, nullable=True)

    last_update: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.now(timezone.utc)
    )
    manual_state: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    raspberry: Mapped["Raspberry"] = relationship("Raspberry", back_populates="devices")
    user: Mapped["User"] = relationship("User", back_populates="devices")
    schedules: Mapped[list["DeviceSchedule"]] = relationship(
        "DeviceSchedule", back_populates="device", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Device id={self.id} name={self.name} mode={self.mode}>"
