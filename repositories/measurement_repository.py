from __future__ import annotations

from datetime import datetime
import logging

from sqlalchemy import case, func, select, text
from sqlalchemy.sql import over
from sqlalchemy.orm import Session
from typing import Iterable

from smart_common.models.provider import Provider
from smart_common.models.provider_measurement import ProviderMeasurement
from smart_common.schemas.normalized_measurement import NormalizedMeasurement

logger = logging.getLogger(__name__)


class MeasurementRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def save_measurement(
        self,
        provider: Provider,
        measurement: NormalizedMeasurement,
        *,
        poll_id: str | None = None,
    ) -> ProviderMeasurement | None:
        if provider.id is None:
            raise ValueError("provider must be persisted before saving measurements")

        last_entry = self._fetch_last_measurement(provider.id)
        if last_entry and self._is_equivalent(last_entry, measurement):
            self._update_last_measurement(
                last_entry,
                measurement,
                provider_id=provider.id,
                poll_id=poll_id,
            )
            return None

        entry = ProviderMeasurement(
            provider_id=provider.id,
            measured_at=measurement.measured_at,
            measured_value=measurement.value,
            measured_unit=measurement.unit,
            metadata_payload=dict(measurement.metadata or {}),
        )

        self.session.add(entry)
        self.session.flush()

        logger.info(
            "Measurement persistence check",
            extra={
                "provider_id": provider.id,
                "poll_id": poll_id,
                "action": "inserted",
            },
        )

        return entry

    def _update_last_measurement(
        self,
        entry: ProviderMeasurement,
        measurement: NormalizedMeasurement,
        *,
        provider_id: int,
        poll_id: str | None,
    ) -> None:
        entry.measured_at = measurement.measured_at
        entry.measured_unit = measurement.unit
        entry.measured_value = measurement.value
        entry.metadata_payload = dict(measurement.metadata or {})
        self.session.add(entry)
        self.session.flush()

        logger.info(
            "Measurement persistence check",
            extra={
                "provider_id": provider_id,
                "poll_id": poll_id,
                "action": "refreshed",
            },
        )

    def _fetch_last_measurement(
        self,
        provider_id: int,
    ) -> ProviderMeasurement | None:
        return (
            self.session.query(ProviderMeasurement)
            .filter_by(provider_id=provider_id)
            .order_by(ProviderMeasurement.measured_at.desc())
            .first()
        )

    def get_last_measurements(
        self,
        provider_ids: Iterable[int],
    ) -> dict[int, ProviderMeasurement]:
        if not provider_ids:
            return {}

        stmt = (
            select(ProviderMeasurement)
            .where(ProviderMeasurement.provider_id.in_(provider_ids))
            .order_by(
                ProviderMeasurement.provider_id, ProviderMeasurement.measured_at.desc()
            )
        )
        results = self.session.execute(stmt).scalars()
        last_by_provider: dict[int, ProviderMeasurement] = {}
        for measurement in results:
            provider_id = measurement.provider_id
            if provider_id not in last_by_provider:
                last_by_provider[provider_id] = measurement
        return last_by_provider

    def _is_equivalent(
        self,
        last_entry: ProviderMeasurement | None,
        measurement: NormalizedMeasurement,
    ) -> bool:
        if last_entry is None:
            return False

        if last_entry.measured_unit != measurement.unit:
            return False

        if last_entry.measured_value is None or measurement.value is None:
            return last_entry.measured_value is None and measurement.value is None
        return float(last_entry.measured_value) == measurement.value

    def list_hourly_energy(
        self,
        *,
        provider_id: int,
        date_start: datetime,
        date_end: datetime,
    ):
        m = ProviderMeasurement

        # ---------- SUBQUERY: liczymy energię cząstkową ----------
        next_ts = over(
            func.lead(m.measured_at),
            partition_by=m.provider_id,
            order_by=m.measured_at,
        )

        hour_end = func.date_trunc("hour", m.measured_at) + text("INTERVAL '1 hour'")

        effective_end = func.least(
            func.coalesce(next_ts, date_end),
            hour_end,
        )

        duration_hours = func.extract("epoch", effective_end - m.measured_at) / 3600.0

        energy_provder_unit_h = m.measured_value * duration_hours

        base_q = (
            select(
                func.date_trunc("hour", m.measured_at).label("hour"),
                energy_provder_unit_h.label("energy"),
            )
            .where(
                m.provider_id == provider_id,
                m.measured_at >= date_start,
                m.measured_at < date_end,
                m.measured_value.isnot(None),
            )
            .subquery()
        )

        # ---------- FINAL QUERY: agregacja ----------
        stmt = (
            select(
                base_q.c.hour,
                func.sum(base_q.c.energy).label("energy"),
            )
            .group_by(base_q.c.hour)
            .order_by(base_q.c.hour)
        )

        return self.session.execute(stmt).all()
