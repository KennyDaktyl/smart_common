from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID as UUIDType
from uuid import uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Numeric,
    String,
    Integer,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from smart_common.core.db import Base
from smart_common.providers.enums import ProviderKind, ProviderType, ProviderVendor
from smart_common.enums.unit import PowerUnit
from smart_common.models.normalized_measurement import NormalizedMeasurement  # noqa: F401


class Provider(Base):
    __tablename__ = "providers"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "vendor",
            "external_id",
            name="uq_providers_user_vendor_external",
        ),
    )

    # ---------- identity ----------
    id: Mapped[int] = mapped_column(primary_key=True)

    uuid: Mapped[UUIDType] = mapped_column(
        UUID(as_uuid=True),
        default=uuid4,
        unique=True,
        nullable=False,
        index=True,
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    microcontroller_id: Mapped[int | None] = mapped_column(
        ForeignKey("microcontrollers.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    name: Mapped[str] = mapped_column(String, nullable=False)

    # ---------- classification ----------
    provider_type: Mapped[ProviderType] = mapped_column(
        Enum(ProviderType, name="provider_type_enum"),
        nullable=False,
    )

    kind: Mapped[ProviderKind] = mapped_column(
        Enum(ProviderKind, name="provider_kind_enum"),
        nullable=False,
    )

    vendor: Mapped[ProviderVendor | None] = mapped_column(
        Enum(ProviderVendor, name="provider_vendor_enum"),
        nullable=True,
    )

    external_id: Mapped[str | None] = mapped_column(String, nullable=True)

    unit: Mapped[PowerUnit | None] = mapped_column(
        Enum(PowerUnit, name="power_unit_enum"),
        nullable=True,
    )

    # ---------- physical range (NOT scheduler rules) ----------
    value_min: Mapped[float | None] = mapped_column(Numeric(12, 4))
    value_max: Mapped[float | None] = mapped_column(Numeric(12, 4))

    # ---------- runtime state ----------
    last_value: Mapped[float | None] = mapped_column(Numeric(12, 4))
    last_measurement_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    expected_interval_sec: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Expected max interval (seconds) between measurements",
    )
    # ---------- lifecycle ----------
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    # ---------- vendor-specific config ----------
    config: Mapped[dict] = mapped_column(JSON, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    last_seen_at: datetime | None
    last_value: float | None
    
    microcontroller = relationship(
        "Microcontroller",
        back_populates="sensor_providers",
        foreign_keys=[microcontroller_id],
    )
    user = relationship("User")
    credentials = relationship(
        "ProviderCredential",
        back_populates="provider",
        uselist=False,
        cascade="all, delete-orphan",
    )

    measurements = relationship(
        "ProviderMeasurement",
        back_populates="provider",
        cascade="all, delete-orphan",
    )


class ProviderCredential(Base):
    __tablename__ = "provider_credentials"

    id: Mapped[int] = mapped_column(primary_key=True)

    provider_id: Mapped[int] = mapped_column(
        ForeignKey("providers.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,  # 1:1
        index=True,
    )

    # --- auth data ---
    login: Mapped[str | None] = mapped_column(String, nullable=True)
    password: Mapped[str | None] = mapped_column(String, nullable=True)
    token: Mapped[str | None] = mapped_column(String, nullable=True)
    refresh_token: Mapped[str | None] = mapped_column(String, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    provider = relationship("Provider", back_populates="credentials")
