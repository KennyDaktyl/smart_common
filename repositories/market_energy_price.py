from __future__ import annotations

from datetime import date, datetime
from typing import Any

from smart_common.models.market_energy_price import MarketEnergyPrice
from smart_common.repositories.base import BaseRepository


class MarketEnergyPriceRepository(BaseRepository[MarketEnergyPrice]):
    model = MarketEnergyPrice
    default_order_by = MarketEnergyPrice.interval_start.desc()

    def upsert_price(
        self,
        *,
        market: str,
        business_date: date,
        interval_start: datetime,
        interval_end: datetime,
        price_value: float,
        currency: str,
        price_unit: str,
        source_updated_at: datetime | None,
        payload: dict[str, Any] | None = None,
    ) -> MarketEnergyPrice:
        entry = (
            self.session.query(MarketEnergyPrice)
            .filter(
                MarketEnergyPrice.market == market,
                MarketEnergyPrice.interval_start == interval_start,
            )
            .one_or_none()
        )

        if entry is None:
            entry = MarketEnergyPrice(
                market=market,
                business_date=business_date,
                interval_start=interval_start,
                interval_end=interval_end,
                price_value=price_value,
                currency=currency,
                price_unit=price_unit,
                source_updated_at=source_updated_at,
                payload=dict(payload or {}),
            )
            self.session.add(entry)
        else:
            entry.business_date = business_date
            entry.interval_end = interval_end
            entry.price_value = price_value
            entry.currency = currency
            entry.price_unit = price_unit
            entry.source_updated_at = source_updated_at
            entry.payload = dict(payload or {})
            self.session.add(entry)

        self.session.flush()
        return entry

    def get_active_at(
        self,
        *,
        market: str,
        timestamp: datetime,
    ) -> MarketEnergyPrice | None:
        return (
            self.session.query(MarketEnergyPrice)
            .filter(
                MarketEnergyPrice.market == market,
                MarketEnergyPrice.interval_start <= timestamp,
                MarketEnergyPrice.interval_end > timestamp,
            )
            .order_by(MarketEnergyPrice.interval_start.desc())
            .first()
        )

    def get_latest_before(
        self,
        *,
        market: str,
        timestamp: datetime,
    ) -> MarketEnergyPrice | None:
        return (
            self.session.query(MarketEnergyPrice)
            .filter(
                MarketEnergyPrice.market == market,
                MarketEnergyPrice.interval_start <= timestamp,
            )
            .order_by(MarketEnergyPrice.interval_start.desc())
            .first()
        )

    def list_between(
        self,
        *,
        market: str,
        date_start: datetime,
        date_end: datetime,
    ) -> list[MarketEnergyPrice]:
        return (
            self.session.query(MarketEnergyPrice)
            .filter(
                MarketEnergyPrice.market == market,
                MarketEnergyPrice.interval_start >= date_start,
                MarketEnergyPrice.interval_start < date_end,
            )
            .order_by(MarketEnergyPrice.interval_start.asc())
            .all()
        )
