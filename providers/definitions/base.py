# smart_common/providers/definitions/base.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Mapping, Type, TYPE_CHECKING

from pydantic import BaseModel

from smart_common.enums.unit import PowerUnit
from smart_common.providers.enums import ProviderKind, ProviderType, ProviderVendor

if TYPE_CHECKING:  # pragma: no cover
    from smart_common.providers.adapters.base import BaseProviderAdapter
    from smart_common.providers.wizard.base import ProviderWizard


Unit = PowerUnit


@dataclass(frozen=True)
class ProviderDefinition:
    vendor: ProviderVendor
    label: str
    provider_type: ProviderType
    kind: ProviderKind
    default_unit: Unit | None
    requires_wizard: bool
    config_schema: Type[BaseModel]
    credentials_schema: Type[BaseModel] | None = None
    adapter_cls: type["BaseProviderAdapter"] | None = None
    adapter_settings: Mapping[str, Any] = field(default_factory=dict)
    wizard_cls: type["ProviderWizard"] | None = None
    default_unit: Unit | None
    default_value_min: float | None = None
    default_value_max: float | None = None
    default_expected_interval_sec: int | None = None


class ProviderDefinitionRegistry:
    _registry: Dict[ProviderVendor, ProviderDefinition] = {}

    @classmethod
    def register(cls, definition: ProviderDefinition) -> ProviderDefinition:
        cls._registry[definition.vendor] = definition
        return definition

    @classmethod
    def get(cls, vendor: ProviderVendor) -> ProviderDefinition | None:
        return cls._registry.get(vendor)

    @classmethod
    def all(cls) -> Mapping[ProviderVendor, ProviderDefinition]:
        return dict(cls._registry)

    @classmethod
    def clear(cls) -> None:
        cls._registry.clear()
