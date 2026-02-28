# models/microcontroller.py
from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID as UUIDType
from uuid import uuid4

from pydantic import BaseModel
from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.dialects.postgresql import JSONB
from smart_common.core.db import Base
from smart_common.enums.microcontroller import MicrocontrollerType
from smart_common.models.microcontroller_sensor_capability import (
    MicrocontrollerSensorCapability,
)


class Microcontroller(Base):
    __tablename__ = "microcontrollers"

    id: Mapped[int] = mapped_column(primary_key=True)

    uuid: Mapped[UUIDType] = mapped_column(
        UUID(as_uuid=True),
        unique=True,
        nullable=False,
        index=True,
        default=uuid4,
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    type: Mapped[MicrocontrollerType] = mapped_column(
        Enum(MicrocontrollerType, name="microcontroller_type_enum"),
        nullable=False,
    )

    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(String)

    software_version: Mapped[str | None] = mapped_column(String)

    max_devices: Mapped[int] = mapped_column(Integer, default=1)

    enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    power_provider_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "providers.id",
            ondelete="SET NULL",
            use_alter=True,
            name="fk_microcontrollers_power_provider_id",
        ),
        nullable=True,
        index=True,
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
    config: Mapped[dict] = mapped_column(
        MutableDict.as_mutable(JSONB),
        nullable=False,
    )

    # --- Relations ---
    user = relationship("User", back_populates="microcontrollers")

    # sensor_providers = relationship(
    #     "Provider",
    #     back_populates="microcontroller",
    #     cascade="all, delete-orphan",
    #     foreign_keys="Provider.microcontroller_id",
    # )

    power_provider = relationship(
        "Provider",
        foreign_keys=[power_provider_id],
    )

    devices = relationship(
        "Device",
        back_populates="microcontroller",
        order_by="Device.id",
        cascade="all, delete-orphan",
    )

    sensor_capabilities = relationship(
        "MicrocontrollerSensorCapability",
        back_populates="microcontroller",
        cascade="all, delete-orphan",
    )

    @property
    def assigned_sensors(self) -> list[str]:
        return [capability.sensor_type for capability in self.sensor_capabilities]

    @property
    def active_provider(self):
        return self.power_provider

    @property
    def user_email(self):
        return self.user.email if self.user else None

    def __repr__(self) -> str:
        return (
            f"<Microcontroller id={self.id} " f"type={self.type} " f"name={self.name}>"
        )
