from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Mapping

from smart_common.models.provider import Provider
from smart_common.models.provider_metric_sample import ProviderMetricSample
from smart_common.models.provider_measurement import ProviderMeasurement
from smart_common.schemas.automation_rule import (
    AutomationRuleComparator,
    AutomationRuleCondition,
    AutomationRuleGroup,
    AutomationRuleGroupOperator,
    AutomationRuleSource,
    BATTERY_SOC_METRIC_KEY,
    build_legacy_power_rule,
)
from smart_common.schemas.scheduler_runtime import Decision, DecisionKind, DueSchedulerEntry


@dataclass(frozen=True)
class _ConditionEvaluation:
    met: bool | None
    reason: str
    measured_value: float | None = None
    measured_unit: str | None = None


class SchedulerDecisionService:
    def decide(
        self,
        *,
        entry: DueSchedulerEntry,
        now_utc: datetime,
        provider: Provider | None,
        latest_measurement: ProviderMeasurement | None,
        latest_metric_samples: Mapping[str, ProviderMetricSample | None] | None = None,
    ) -> Decision:
        rule = entry.activation_rule or _legacy_rule_from_entry(entry)
        if rule is None:
            return Decision(
                kind=DecisionKind.ALLOW_ON,
                trigger_reason="SCHEDULER_MATCH",
            )

        evaluation = self._evaluate_rule_group(
            rule=rule,
            now_utc=now_utc,
            provider=provider,
            latest_measurement=latest_measurement,
            latest_metric_samples=latest_metric_samples or {},
        )

        if evaluation.met is True:
            return Decision(
                kind=DecisionKind.ALLOW_ON,
                trigger_reason="SCHEDULER_MATCH",
                measured_value=evaluation.measured_value,
                measured_unit=evaluation.measured_unit,
            )
        if evaluation.met is False:
            return Decision(
                kind=DecisionKind.SKIP_THRESHOLD_NOT_MET,
                trigger_reason=evaluation.reason,
                measured_value=evaluation.measured_value,
                measured_unit=evaluation.measured_unit,
            )

        return Decision(
            kind=DecisionKind.SKIP_NO_POWER_DATA,
            trigger_reason=evaluation.reason,
            measured_value=evaluation.measured_value,
            measured_unit=evaluation.measured_unit,
        )

    def _evaluate_rule_group(
        self,
        *,
        rule: AutomationRuleGroup,
        now_utc: datetime,
        provider: Provider | None,
        latest_measurement: ProviderMeasurement | None,
        latest_metric_samples: Mapping[str, ProviderMetricSample | None],
    ) -> _ConditionEvaluation:
        evaluations = [
            self._evaluate_rule_item(
                item=item,
                now_utc=now_utc,
                provider=provider,
                latest_measurement=latest_measurement,
                latest_metric_samples=latest_metric_samples,
            )
            for item in (rule.items or [])
        ]
        return _combine_group_evaluations(rule.operator, evaluations)

    def _evaluate_rule_item(
        self,
        *,
        item: AutomationRuleCondition | AutomationRuleGroup,
        now_utc: datetime,
        provider: Provider | None,
        latest_measurement: ProviderMeasurement | None,
        latest_metric_samples: Mapping[str, ProviderMetricSample | None],
    ) -> _ConditionEvaluation:
        if isinstance(item, AutomationRuleCondition):
            return self._evaluate_condition(
                condition=item,
                now_utc=now_utc,
                provider=provider,
                latest_measurement=latest_measurement,
                latest_metric_samples=latest_metric_samples,
            )

        return self._evaluate_rule_group(
            rule=item,
            now_utc=now_utc,
            provider=provider,
            latest_measurement=latest_measurement,
            latest_metric_samples=latest_metric_samples,
        )

    def _evaluate_condition(
        self,
        *,
        condition: AutomationRuleCondition,
        now_utc: datetime,
        provider: Provider | None,
        latest_measurement: ProviderMeasurement | None,
        latest_metric_samples: Mapping[str, ProviderMetricSample | None],
    ) -> _ConditionEvaluation:
        if not provider or not provider.enabled:
            return _ConditionEvaluation(None, "POWER_PROVIDER_UNAVAILABLE")

        if provider.expected_interval_sec is None or provider.expected_interval_sec <= 0:
            return _ConditionEvaluation(None, "POWER_INTERVAL_MISSING")

        if condition.source == AutomationRuleSource.PROVIDER_PRIMARY_POWER:
            return _evaluate_primary_power_condition(
                condition=condition,
                now_utc=now_utc,
                provider=provider,
                latest_measurement=latest_measurement,
            )

        if condition.source == AutomationRuleSource.PROVIDER_BATTERY_SOC:
            return _evaluate_battery_soc_condition(
                condition=condition,
                now_utc=now_utc,
                provider=provider,
                latest_sample=latest_metric_samples.get(BATTERY_SOC_METRIC_KEY),
            )

        return _ConditionEvaluation(None, "RULE_SOURCE_UNSUPPORTED")


def _evaluate_primary_power_condition(
    *,
    condition: AutomationRuleCondition,
    now_utc: datetime,
    provider: Provider,
    latest_measurement: ProviderMeasurement | None,
) -> _ConditionEvaluation:
    if latest_measurement is None:
        return _ConditionEvaluation(None, "POWER_MISSING")

    measured_at = _to_utc_aware(latest_measurement.measured_at)
    age_sec = (now_utc - measured_at).total_seconds()
    if age_sec > provider.expected_interval_sec:
        return _ConditionEvaluation(None, "POWER_STALE")

    if latest_measurement.measured_value is None:
        return _ConditionEvaluation(None, "POWER_MISSING")

    measured_unit = (
        latest_measurement.measured_unit
        or (provider.unit.value if provider.unit is not None else None)
        or condition.unit
    )
    normalized_value = _convert_power_value(
        float(latest_measurement.measured_value),
        measured_unit,
        condition.unit,
    )
    if normalized_value is None:
        return _ConditionEvaluation(None, "POWER_UNIT_UNSUPPORTED")

    is_match = _compare_value(
        normalized_value,
        condition.value,
        condition.comparator,
    )
    return _ConditionEvaluation(
        is_match,
        "SCHEDULER_MATCH" if is_match else "THRESHOLD_NOT_MET",
        measured_value=normalized_value,
        measured_unit=condition.unit,
    )


def _evaluate_battery_soc_condition(
    *,
    condition: AutomationRuleCondition,
    now_utc: datetime,
    provider: Provider,
    latest_sample: ProviderMetricSample | None,
) -> _ConditionEvaluation:
    if latest_sample is None:
        return _ConditionEvaluation(None, "BATTERY_SOC_MISSING")

    measured_at = _to_utc_aware(latest_sample.measured_at)
    age_sec = (now_utc - measured_at).total_seconds()
    if age_sec > provider.expected_interval_sec:
        return _ConditionEvaluation(None, "BATTERY_SOC_STALE")

    measured_value = float(latest_sample.value)
    measured_unit = latest_sample.unit or condition.unit
    if measured_unit != condition.unit:
        return _ConditionEvaluation(None, "BATTERY_SOC_UNIT_UNSUPPORTED")

    is_match = _compare_value(
        measured_value,
        condition.value,
        condition.comparator,
    )
    return _ConditionEvaluation(
        is_match,
        "SCHEDULER_MATCH" if is_match else "THRESHOLD_NOT_MET",
        measured_value=measured_value,
        measured_unit=measured_unit,
    )


def _compare_value(
    measured_value: float,
    threshold_value: float,
    comparator: AutomationRuleComparator,
) -> bool:
    if comparator == AutomationRuleComparator.GT:
        return measured_value > threshold_value
    if comparator == AutomationRuleComparator.GTE:
        return measured_value >= threshold_value
    if comparator == AutomationRuleComparator.LT:
        return measured_value < threshold_value
    if comparator == AutomationRuleComparator.LTE:
        return measured_value <= threshold_value
    return False


def _legacy_rule_from_entry(entry: DueSchedulerEntry) -> AutomationRuleGroup | None:
    if not entry.use_power_threshold or entry.power_threshold_value is None:
        return None
    return build_legacy_power_rule(
        value=entry.power_threshold_value,
        unit=entry.power_threshold_unit or "W",
    )


def _combine_group_evaluations(
    operator: AutomationRuleGroupOperator,
    evaluations: list[_ConditionEvaluation],
) -> _ConditionEvaluation:
    if operator == AutomationRuleGroupOperator.ALL:
        failed = next((item for item in evaluations if item.met is False), None)
        if failed is not None:
            return failed

        missing = next((item for item in evaluations if item.met is None), None)
        if missing is not None:
            return missing

        return evaluations[0]

    matched = next((item for item in evaluations if item.met is True), None)
    if matched is not None:
        return matched

    failed = next((item for item in evaluations if item.met is False), None)
    if failed is not None:
        return failed

    return evaluations[0]


def _convert_power_value(
    value: float,
    source_unit: str | None,
    target_unit: str,
) -> float | None:
    source_multiplier = _power_unit_multiplier(source_unit)
    target_multiplier = _power_unit_multiplier(target_unit)
    if source_multiplier is None or target_multiplier is None:
        return None
    value_in_watts = value * source_multiplier
    return value_in_watts / target_multiplier


def _power_unit_multiplier(unit: str | None) -> float | None:
    if unit is None:
        return None
    normalized = unit.strip().lower()
    if normalized == "w":
        return 1.0
    if normalized == "kw":
        return 1000.0
    if normalized == "mw":
        return 1000000.0
    return None


def _to_utc_aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
