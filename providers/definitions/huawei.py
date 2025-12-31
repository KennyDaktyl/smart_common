from __future__ import annotations

from smart_common.enums.unit import PowerUnit
from smart_common.providers.adapters.huawei import HuaweiProviderAdapter
from smart_common.providers.definitions.base import ProviderDefinition, ProviderDefinitionRegistry
from smart_common.providers.enums import ProviderKind, ProviderType, ProviderVendor
from smart_common.providers.provider_config.config import provider_settings
from smart_common.providers.provider_config.credentials import UsernamePasswordCredentials
from smart_common.providers.provider_config.huawei.final import HuaweiProviderConfig
from smart_common.providers.wizard.huawei.wizard import HuaweiWizard


ProviderDefinitionRegistry.register(
    ProviderDefinition(
        vendor=ProviderVendor.HUAWEI,
        label="Huawei FusionSolar",
        provider_type=ProviderType.API,
        kind=ProviderKind.POWER,
        default_unit=PowerUnit.KILOWATT,
        requires_wizard=True,
        config_schema=HuaweiProviderConfig,
        credentials_schema=UsernamePasswordCredentials,
        adapter_cls=HuaweiProviderAdapter,
        adapter_settings={
            "base_url": provider_settings.HUAWEI_BASE_URL,
            "timeout": provider_settings.HUAWEI_TIMEOUT,
            "max_retries": provider_settings.HUAWEI_MAX_RETRIES,
        },
        wizard_cls=HuaweiWizard,
        default_unit=PowerUnit.KILOWATT,
        default_value_min=0.0,
        default_value_max=10.0,
        default_expected_interval_sec=180,

    )
)
