# models/provider.py
from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID as UUIDType
from uuid import uuid4

from sqlalchemy import JSON, Boolean, DateTime, Enum, ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from smart_common.core.db import Base
from smart_common.enums.provider import ProviderKind, ProviderType, ProviderVendor
from smart_common.enums.unit import PowerUnit


class Provider(Base):
    __tablename__ = "providers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    uuid: Mapped[UUIDType] = mapped_column(
        UUID(as_uuid=True),
        unique=True,
        nullable=False,
        index=True,
        default=uuid4,
    )

    microcontroller_id: Mapped[int] = mapped_column(
        ForeignKey("microcontrollers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(String, nullable=False)

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

    model: Mapped[str | None] = mapped_column(String)

    unit: Mapped[PowerUnit | None] = mapped_column(
        Enum(PowerUnit, name="power_unit_enum"),
        nullable=True,
    )

    min_value: Mapped[float | None] = mapped_column(Numeric(12, 4))
    max_value: Mapped[float | None] = mapped_column(Numeric(12, 4))

    last_value: Mapped[float | None] = mapped_column(Numeric(12, 4))
    last_measurement_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    polling_interval_sec: Mapped[int | None] = mapped_column(Integer)

    enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    config: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

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
        back_populates="providers",
    )

    def __repr__(self) -> str:
        return (
            f"<Provider id={self.id} "
            f"type={self.provider_type} "
            f"kind={self.kind} "
            f"vendor={self.vendor}>"
        )
