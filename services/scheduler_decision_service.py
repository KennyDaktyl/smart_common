from __future__ import annotations

from datetime import datetime, timezone

from smart_common.models.provider import Provider
from smart_common.models.provider_measurement import ProviderMeasurement
from smart_common.schemas.scheduler_runtime import Decision, DecisionKind, DueSchedulerEntry


class SchedulerDecisionService:
    def decide(
        self,
        *,
        entry: DueSchedulerEntry,
        now_utc: datetime,
        provider: Provider | None,
        latest_measurement: ProviderMeasurement | None,
    ) -> Decision:
        if not entry.use_power_threshold:
            return Decision(
                kind=DecisionKind.ALLOW_ON,
                trigger_reason="SCHEDULER_MATCH",
            )

        threshold_value = entry.power_threshold_value
        if threshold_value is None:
            return Decision(DecisionKind.SKIP_NO_POWER_DATA, "THRESHOLD_CONFIG_MISSING")

        if not provider or not provider.enabled:
            return Decision(DecisionKind.SKIP_NO_POWER_DATA, "POWER_PROVIDER_UNAVAILABLE")

        if provider.expected_interval_sec is None or provider.expected_interval_sec <= 0:
            return Decision(DecisionKind.SKIP_NO_POWER_DATA, "POWER_INTERVAL_MISSING")

        if not latest_measurement:
            return Decision(DecisionKind.SKIP_NO_POWER_DATA, "POWER_MISSING")

        measured_at = _to_utc_aware(latest_measurement.measured_at)
        age_sec = (now_utc - measured_at).total_seconds()
        if age_sec > provider.expected_interval_sec:
            return Decision(DecisionKind.SKIP_NO_POWER_DATA, "POWER_STALE")

        if latest_measurement.measured_value is None:
            return Decision(DecisionKind.SKIP_NO_POWER_DATA, "POWER_MISSING")

        measured_value = float(latest_measurement.measured_value)
        measured_unit = (
            latest_measurement.measured_unit
            or (provider.unit.value if provider.unit is not None else None)
            or entry.power_threshold_unit
        )

        if measured_value >= threshold_value:
            return Decision(
                kind=DecisionKind.ALLOW_ON,
                trigger_reason="SCHEDULER_MATCH",
                measured_value=measured_value,
                measured_unit=measured_unit,
            )

        return Decision(
            kind=DecisionKind.SKIP_THRESHOLD_NOT_MET,
            trigger_reason="THRESHOLD_NOT_MET",
            measured_value=measured_value,
            measured_unit=measured_unit,
        )


def _to_utc_aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
