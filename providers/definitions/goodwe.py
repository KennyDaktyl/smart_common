from __future__ import annotations

from smart_common.enums.unit import PowerUnit
from smart_common.providers.adapters.goodwe import GoodWeProviderAdapter
from smart_common.providers.definitions.base import (
    ProviderDefinition,
    ProviderDefinitionRegistry,
)
from smart_common.providers.enums import ProviderKind, ProviderType, ProviderVendor

from smart_common.providers.provider_config.goodwe import (
    GoodWeProviderConfig,
    goodwe_integration_settings,
)
from smart_common.providers.wizard.goodwe.wizard import GoodWeWizard


ProviderDefinitionRegistry.register(
    ProviderDefinition(
        vendor=ProviderVendor.GOODWE,
        label="GoodWe SEMS",
        provider_type=ProviderType.API,
        kind=ProviderKind.POWER,
        default_unit=PowerUnit.WATT,
        requires_wizard=True,
        config_schema=GoodWeProviderConfig,
        adapter_cls=GoodWeProviderAdapter,
        adapter_settings={
            "timeout": goodwe_integration_settings.GOODWE_TIMEOUT,
            "max_retries": goodwe_integration_settings.GOODWE_MAX_RETRIES,
        },
        wizard_cls=GoodWeWizard,
        default_unit=PowerUnit.WATT,
        default_value_min=0.0,
        default_value_max=20000.0,
        default_expected_interval_sec=120,

    )
)
