from __future__ import annotations

from enum import Enum

from pydantic import Field, model_validator

from smart_common.schemas.base import APIModel

BATTERY_SOC_METRIC_KEY = "battery_soc"
BATTERY_SOC_UNIT = "%"
POWER_RULE_UNITS = frozenset({"W", "kW", "MW"})


class AutomationRuleGroupOperator(str, Enum):
    ALL = "ALL"
    ANY = "ANY"


class AutomationRuleComparator(str, Enum):
    GT = "gt"
    GTE = "gte"
    LT = "lt"
    LTE = "lte"


class AutomationRuleSource(str, Enum):
    PROVIDER_PRIMARY_POWER = "provider_primary_power"
    PROVIDER_BATTERY_SOC = "provider_battery_soc"


class AutomationRuleCondition(APIModel):
    source: AutomationRuleSource
    comparator: AutomationRuleComparator = AutomationRuleComparator.GTE
    value: float = Field(..., ge=0)
    unit: str

    @model_validator(mode="after")
    def validate_for_source(self):
        if self.source == AutomationRuleSource.PROVIDER_BATTERY_SOC:
            if self.unit != BATTERY_SOC_UNIT:
                raise ValueError("provider_battery_soc conditions must use % unit")
            if self.value > 100:
                raise ValueError("provider_battery_soc value must be between 0 and 100")
            return self

        if self.source == AutomationRuleSource.PROVIDER_PRIMARY_POWER:
            if self.unit not in POWER_RULE_UNITS:
                raise ValueError(
                    f"provider_primary_power unit must be one of: {', '.join(sorted(POWER_RULE_UNITS))}"
                )
            return self

        raise ValueError(f"unsupported automation rule source: {self.source}")


class AutomationRuleGroup(APIModel):
    operator: AutomationRuleGroupOperator = AutomationRuleGroupOperator.ANY
    conditions: list[AutomationRuleCondition] = Field(min_length=1)


def build_legacy_power_rule(
    *,
    value: float,
    unit: str,
    comparator: AutomationRuleComparator = AutomationRuleComparator.GTE,
) -> AutomationRuleGroup:
    return AutomationRuleGroup(
        operator=AutomationRuleGroupOperator.ANY,
        conditions=[
            AutomationRuleCondition(
                source=AutomationRuleSource.PROVIDER_PRIMARY_POWER,
                comparator=comparator,
                value=value,
                unit=unit,
            )
        ],
    )


def extract_legacy_power_threshold(
    rule: AutomationRuleGroup | None,
) -> tuple[float, str] | None:
    if rule is None:
        return None
    if rule.operator != AutomationRuleGroupOperator.ANY:
        return None
    if len(rule.conditions) != 1:
        return None

    condition = rule.conditions[0]
    if condition.source != AutomationRuleSource.PROVIDER_PRIMARY_POWER:
        return None
    if condition.comparator != AutomationRuleComparator.GTE:
        return None

    return condition.value, condition.unit


def uses_source(
    rule: AutomationRuleGroup | None,
    source: AutomationRuleSource,
) -> bool:
    if rule is None:
        return False
    return any(condition.source == source for condition in rule.conditions)


def source_metric_key(source: AutomationRuleSource) -> str | None:
    if source == AutomationRuleSource.PROVIDER_BATTERY_SOC:
        return BATTERY_SOC_METRIC_KEY
    return None
