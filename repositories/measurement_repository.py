from __future__ import annotations

from datetime import datetime
from collections.abc import Mapping
import logging
from typing import Any, Iterable

from sqlalchemy import select

from smart_common.models.provider import Provider
from smart_common.models.provider_metric_definition import ProviderMetricDefinition
from smart_common.models.provider_metric_sample import ProviderMetricSample
from smart_common.models.provider_measurement import ProviderMeasurement
from smart_common.repositories.base import BaseRepository
from smart_common.enums.provider_telemetry import ProviderTelemetryCapability
from smart_common.enums.provider_telemetry import (
    TelemetryAggregationMode,
    TelemetryChartType,
)
from smart_common.schemas.normalized_measurement import NormalizedMeasurement

logger = logging.getLogger(__name__)

SYSTEM_METADATA_KEYS = frozenset(
    {
        "unit_source",
        "power_source",
        "measurement_source",
        "error",
    }
)


def _make_json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value

    if isinstance(value, datetime):
        return value.isoformat()

    if isinstance(value, Mapping):
        return {str(key): _make_json_safe(item) for key, item in value.items()}

    if isinstance(value, (list, tuple, set)):
        return [_make_json_safe(item) for item in value]

    return str(value)


def _normalize_metadata(metadata: Mapping[str, Any] | None) -> dict[str, Any]:
    if not isinstance(metadata, Mapping):
        return {}

    return {str(key): _make_json_safe(value) for key, value in metadata.items()}


def _split_metadata(metadata: Mapping[str, Any] | None) -> tuple[dict[str, Any], dict[str, Any]]:
    normalized = _normalize_metadata(metadata)

    system_metadata: dict[str, Any] = {}
    extra_data: dict[str, Any] = {}
    for key, value in normalized.items():
        if key in SYSTEM_METADATA_KEYS:
            system_metadata[key] = value
        else:
            extra_data[key] = value

    return system_metadata, extra_data


def _deep_merge_dict(base: dict[str, Any], updates: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in updates.items():
        current = merged.get(key)
        if isinstance(current, Mapping) and isinstance(value, Mapping):
            merged[key] = _deep_merge_dict(dict(current), dict(value))
        else:
            merged[key] = value
    return merged


def _count_nested_entries(value: Any) -> int:
    if isinstance(value, Mapping):
        return len(value) + sum(_count_nested_entries(item) for item in value.values())
    if isinstance(value, list):
        return len(value) + sum(_count_nested_entries(item) for item in value)
    return 1


class MeasurementRepository(BaseRepository[ProviderMeasurement]):
    model = ProviderMeasurement

    @staticmethod
    def split_metadata(metadata: Mapping[str, Any] | None) -> tuple[dict[str, Any], dict[str, Any]]:
        return _split_metadata(metadata)

    def save_measurement(
        self,
        provider: Provider,
        measurement: NormalizedMeasurement,
        *,
        poll_id: str | None = None,
        force_insert: bool = False,
    ) -> ProviderMeasurement | None:
        if provider.id is None:
            raise ValueError("provider must be persisted before saving measurements")

        incoming_metadata = _normalize_metadata(measurement.metadata)
        last_entry = self._fetch_last_measurement(provider.id)
        if (
            not force_insert
            and last_entry
            and self._is_equivalent(last_entry, measurement)
        ):
            self._update_last_measurement(
                last_entry,
                measurement,
                metadata_parts=self.split_metadata(incoming_metadata),
                provider_id=provider.id,
                poll_id=poll_id,
                incoming_metadata=incoming_metadata,
            )
            return None

        system_metadata, extra_data = self.split_metadata(incoming_metadata)
        entry = ProviderMeasurement(
            provider_id=provider.id,
            measured_at=measurement.measured_at,
            measured_value=measurement.value,
            measured_unit=measurement.unit,
            metadata_payload=system_metadata,
            extra_data=extra_data,
        )

        self.session.add(entry)
        self.session.flush()
        self._sync_metric_samples(
            provider=provider,
            entry=entry,
            measurement=measurement,
        )

        logger.info(
            "Measurement persistence check",
            extra={
                "provider_id": provider.id,
                "poll_id": poll_id,
                "action": "inserted",
                "incoming_metadata_keys": sorted(incoming_metadata.keys()),
                "incoming_metadata_size": _count_nested_entries(incoming_metadata),
                "system_metadata_keys": sorted(system_metadata.keys()),
                "extra_data_keys": sorted(extra_data.keys()),
                "extra_data_size": _count_nested_entries(extra_data),
                "force_insert": force_insert,
            },
        )

        return entry

    def _update_last_measurement(
        self,
        entry: ProviderMeasurement,
        measurement: NormalizedMeasurement,
        *,
        metadata_parts: tuple[dict[str, Any], dict[str, Any]],
        provider_id: int,
        poll_id: str | None,
        incoming_metadata: dict[str, Any],
    ) -> None:
        system_metadata, extra_data = metadata_parts
        entry.measured_at = measurement.measured_at
        entry.measured_unit = measurement.unit
        entry.measured_value = measurement.value
        entry.metadata_payload = system_metadata
        existing_extra_data = _normalize_metadata(entry.extra_data)
        entry.extra_data = _deep_merge_dict(existing_extra_data, extra_data)
        self.session.add(entry)
        self.session.flush()
        self._replace_metric_samples(
            provider=provider_id,
            entry=entry,
            measurement=measurement,
        )

        logger.info(
            "Measurement persistence check",
            extra={
                "provider_id": provider_id,
                "poll_id": poll_id,
                "action": "refreshed",
                "incoming_metadata_keys": sorted(incoming_metadata.keys()),
                "incoming_metadata_size": _count_nested_entries(incoming_metadata),
                "system_metadata_keys": sorted(system_metadata.keys()),
                "extra_data_keys": sorted(extra_data.keys()),
                "extra_data_size": _count_nested_entries(extra_data),
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
                ProviderMeasurement.provider_id,
                ProviderMeasurement.measured_at.desc(),
            )
        )
        results = self.session.execute(stmt).scalars()

        last_by_provider: dict[int, ProviderMeasurement] = {}
        for measurement in results:
            if measurement.provider_id not in last_by_provider:
                last_by_provider[measurement.provider_id] = measurement

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

    def list_metric_definitions(
        self,
        *,
        provider_id: int,
    ) -> list[ProviderMetricDefinition]:
        return (
            self.session.query(ProviderMetricDefinition)
            .filter(ProviderMetricDefinition.provider_id == provider_id)
            .order_by(ProviderMetricDefinition.metric_key.asc())
            .all()
        )

    def get_metric_definition(
        self,
        *,
        provider_id: int,
        metric_key: str,
    ) -> ProviderMetricDefinition | None:
        return (
            self.session.query(ProviderMetricDefinition)
            .filter(
                ProviderMetricDefinition.provider_id == provider_id,
                ProviderMetricDefinition.metric_key == metric_key,
            )
            .first()
        )

    def list_metric_samples(
        self,
        *,
        provider_id: int,
        metric_key: str,
        date_start: datetime,
        date_end: datetime,
    ) -> list[ProviderMetricSample]:
        return (
            self.session.query(ProviderMetricSample)
            .filter(
                ProviderMetricSample.provider_id == provider_id,
                ProviderMetricSample.metric_key == metric_key,
                ProviderMetricSample.measured_at >= date_start,
                ProviderMetricSample.measured_at <= date_end,
            )
            .order_by(ProviderMetricSample.measured_at)
            .all()
        )

    def list_power_samples(
        self,
        *,
        provider_id: int,
        date_start: datetime,
        date_end: datetime,
    ) -> list[tuple[datetime, float]]:
        return (
            self.session.query(
                ProviderMeasurement.measured_at,
                ProviderMeasurement.measured_value,
            )
            .filter(
                ProviderMeasurement.provider_id == provider_id,
                ProviderMeasurement.measured_at >= date_start,
                ProviderMeasurement.measured_at <= date_end,
                ProviderMeasurement.measured_value.isnot(None),
            )
            .order_by(ProviderMeasurement.measured_at)
            .all()
        )

    def list_measurements(
        self,
        *,
        provider_id: int,
        date_start: datetime,
        date_end: datetime,
    ) -> list[ProviderMeasurement]:
        return (
            self.session.query(ProviderMeasurement)
            .filter(
                ProviderMeasurement.provider_id == provider_id,
                ProviderMeasurement.measured_at >= date_start,
                ProviderMeasurement.measured_at <= date_end,
            )
            .order_by(ProviderMeasurement.measured_at)
            .all()
        )

    def get_last_power_sample_before(
        self,
        *,
        provider_id: int,
        before: datetime,
    ) -> tuple[datetime, float] | None:
        return (
            self.session.query(
                ProviderMeasurement.measured_at,
                ProviderMeasurement.measured_value,
            )
            .filter(
                ProviderMeasurement.provider_id == provider_id,
                ProviderMeasurement.measured_at < before,
                ProviderMeasurement.measured_value.isnot(None),
            )
            .order_by(ProviderMeasurement.measured_at.desc())
            .first()
        )

    def _replace_metric_samples(
        self,
        *,
        provider: int,
        entry: ProviderMeasurement,
        measurement: NormalizedMeasurement,
    ) -> None:
        self.session.query(ProviderMetricSample).filter(
            ProviderMetricSample.provider_measurement_id == entry.id,
        ).delete(synchronize_session=False)
        self.session.flush()
        persisted_provider = self.session.get(Provider, provider)
        if persisted_provider is None:
            return
        self._sync_metric_samples(
            provider=persisted_provider,
            entry=entry,
            measurement=measurement,
        )

    def _sync_metric_samples(
        self,
        *,
        provider: Provider,
        entry: ProviderMeasurement,
        measurement: NormalizedMeasurement,
    ) -> None:
        capabilities_seen: set[ProviderTelemetryCapability] = set()

        for metric in measurement.extra_metrics:
            if metric.value is None:
                continue

            definition = self._upsert_metric_definition(
                provider_id=provider.id,
                metric_key=metric.key,
                label=metric.label,
                unit=metric.unit,
                chart_type=metric.chart_type,
                aggregation_mode=metric.aggregation_mode,
                capability_tag=metric.capability_tag,
            )
            sample = ProviderMetricSample(
                provider_id=provider.id,
                provider_measurement_id=entry.id,
                metric_key=definition.metric_key,
                measured_at=measurement.measured_at,
                value=metric.value,
                unit=metric.unit,
                metadata_payload=_normalize_metadata(metric.metadata),
            )
            self.session.add(sample)

            if metric.capability_tag is not None:
                capabilities_seen.add(metric.capability_tag)

        if capabilities_seen:
            self._promote_provider_capabilities(
                provider=provider,
                capabilities=capabilities_seen,
            )

        self.session.flush()

    def _upsert_metric_definition(
        self,
        *,
        provider_id: int,
        metric_key: str,
        label: str,
        unit: str | None,
        chart_type: TelemetryChartType,
        aggregation_mode: TelemetryAggregationMode,
        capability_tag: ProviderTelemetryCapability | None,
    ) -> ProviderMetricDefinition:
        definition = (
            self.session.query(ProviderMetricDefinition)
            .filter(
                ProviderMetricDefinition.provider_id == provider_id,
                ProviderMetricDefinition.metric_key == metric_key,
            )
            .first()
        )

        if definition is None:
            definition = ProviderMetricDefinition(
                provider_id=provider_id,
                metric_key=metric_key,
                label=label,
                unit=unit,
                chart_type=chart_type,
                aggregation_mode=aggregation_mode,
                capability_tag=capability_tag,
            )
        else:
            definition.label = label
            definition.unit = unit
            definition.chart_type = chart_type
            definition.aggregation_mode = aggregation_mode
            definition.capability_tag = capability_tag

        self.session.add(definition)
        self.session.flush()
        return definition

    def _promote_provider_capabilities(
        self,
        *,
        provider: Provider,
        capabilities: set[ProviderTelemetryCapability],
    ) -> None:
        if (
            ProviderTelemetryCapability.POWER_METER in capabilities
            and not provider.has_power_meter
        ):
            provider.has_power_meter = True

        if (
            ProviderTelemetryCapability.ENERGY_STORAGE in capabilities
            and not provider.has_energy_storage
        ):
            provider.has_energy_storage = True

        self.session.add(provider)
