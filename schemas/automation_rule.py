from __future__ import annotations

from enum import Enum
from typing import Iterable, Mapping

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
    items: list[AutomationRuleCondition | AutomationRuleGroup] | None = Field(
        default=None
    )
    conditions: list[AutomationRuleCondition] | None = Field(
        default=None,
        exclude=True,
    )

    @model_validator(mode="before")
    @classmethod
    def migrate_legacy_conditions(cls, value: object):
        if not isinstance(value, Mapping):
            return value

        data = dict(value)
        if data.get("items") is None and data.get("conditions") is not None:
            data["items"] = data.get("conditions")
        return data

    @model_validator(mode="after")
    def validate_items(self):
        if self.items is None and self.conditions is None:
            raise ValueError("automation rule group requires items or conditions")

        if self.items is not None and self.conditions is not None:
            if len(self.items) != len(self.conditions):
                raise ValueError(
                    "automation rule group cannot define both items and conditions"
                )

        if self.items is None:
            self.items = list(self.conditions or [])

        if not self.items:
            raise ValueError("automation rule group must contain at least one item")

        self.conditions = None
        return self


AutomationRuleGroup.model_rebuild()


def build_legacy_power_rule(
    *,
    value: float,
    unit: str,
    comparator: AutomationRuleComparator = AutomationRuleComparator.GTE,
) -> AutomationRuleGroup:
    return AutomationRuleGroup(
        operator=AutomationRuleGroupOperator.ANY,
        items=[
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

    items = rule.items or []
    if len(items) != 1:
        return None

    condition = items[0]
    if not isinstance(condition, AutomationRuleCondition):
        return None
    if condition.source != AutomationRuleSource.PROVIDER_PRIMARY_POWER:
        return None
    if condition.comparator != AutomationRuleComparator.GTE:
        return None

    return condition.value, condition.unit


def iter_conditions(
    rule: AutomationRuleGroup | None,
) -> Iterable[AutomationRuleCondition]:
    if rule is None:
        return []
    return list(_iter_nodes(rule))


def uses_source(
    rule: AutomationRuleGroup | None,
    source: AutomationRuleSource,
) -> bool:
    if rule is None:
        return False
    return any(condition.source == source for condition in _iter_nodes(rule))


def source_metric_key(source: AutomationRuleSource) -> str | None:
    if source == AutomationRuleSource.PROVIDER_BATTERY_SOC:
        return BATTERY_SOC_METRIC_KEY
    return None


def _iter_nodes(
    rule: AutomationRuleGroup,
) -> Iterable[AutomationRuleCondition]:
    for item in rule.items or []:
        if isinstance(item, AutomationRuleCondition):
            yield item
            continue
        yield from _iter_nodes(item)
