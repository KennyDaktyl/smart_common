from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import Date, DateTime, JSON, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from smart_common.core.db import Base


class MarketEnergyPrice(Base):
    __tablename__ = "market_energy_prices"
    __table_args__ = (
        UniqueConstraint(
            "market",
            "interval_start",
            name="uq_market_energy_prices_market_interval_start",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    market: Mapped[str] = mapped_column(String(length=32), nullable=False, index=True)
    business_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    interval_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    interval_end: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    price_value: Mapped[float] = mapped_column(Numeric(12, 6), nullable=False)
    currency: Mapped[str] = mapped_column(
        String(length=8),
        nullable=False,
        default="PLN",
    )
    price_unit: Mapped[str] = mapped_column(
        String(length=16),
        nullable=False,
        default="MWh",
    )
    source_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
