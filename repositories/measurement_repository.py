from __future__ import annotations

from sqlalchemy.orm import Session

from smart_common.models.provider import Provider
from smart_common.models.provider_measurement import ProviderMeasurement
from smart_common.models.normalized_measurement import NormalizedMeasurement


class MeasurementRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def save_measurement(
        self,
        provider: Provider,
        measurement: NormalizedMeasurement,
    ) -> ProviderMeasurement | None:
        if provider.id is None:
            raise ValueError("provider must be persisted before saving measurements")

        last_entry = self._fetch_last_measurement(provider.id)
        should_persist = self._should_persist(last_entry, measurement)
        self._update_provider_state(provider, measurement)

        if not should_persist:
            return None

        entry = ProviderMeasurement(
            provider_id=provider.id,
            measured_at=measurement.measured_at,
            measured_value=measurement.value,
            measured_unit=measurement.unit,
            metadata=dict(measurement.metadata or {}),
        )
        self.session.add(entry)
        self.session.flush()
        return entry

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

    def _should_persist(
        self,
        last_entry: ProviderMeasurement | None,
        measurement: NormalizedMeasurement,
    ) -> bool:
        if last_entry is None:
            return True

        if last_entry.measured_value != measurement.value:
            return True

        if last_entry.measured_unit != measurement.unit:
            return True

        return False

    def _update_provider_state(
        self,
        provider: Provider,
        measurement: NormalizedMeasurement,
    ) -> None:
        provider.last_value = measurement.value
        provider.last_measurement_at = measurement.measured_at
        self.session.add(provider)
