from __future__ import annotations

from typing import Mapping

from smart_common.enums.sensor import SensorType
from smart_common.enums.unit import PowerUnit
from smart_common.providers.definitions.base import (
    ProviderDefinition,
    ProviderDefinitionRegistry,
)
from smart_common.providers.enums import ProviderKind, ProviderType, ProviderVendor
from smart_common.providers.provider_config.sensor_base import SensorThresholdConfig

# Import provider-specific modules to register their definitions.
from smart_common.providers.definitions import goodwe  # noqa: F401
from smart_common.providers.definitions import huawei  # noqa: F401


def _register_sensor(
    vendor: ProviderVendor,
    *,
    label: str,
    kind: ProviderKind,
    default_unit: PowerUnit,
) -> None:
    ProviderDefinitionRegistry.register(
        ProviderDefinition(
            vendor=vendor,
            label=label,
            provider_type=ProviderType.SENSOR,
            kind=kind,
            default_unit=default_unit,
            requires_wizard=False,
            config_schema=SensorThresholdConfig,
        )
    )


# _register_sensor(
#     ProviderVendor.DHT22,
#     label="DHT22 Sensor",
#     kind=ProviderKind.TEMPERATURE,
#     default_unit=PowerUnit.CELSIUS,
# )
# _register_sensor(
#     ProviderVendor.BME280,
#     label="BME280 Sensor",
#     kind=ProviderKind.TEMPERATURE,
#     default_unit=PowerUnit.CELSIUS,
# )
# _register_sensor(
#     ProviderVendor.BH1750,
#     label="BH1750 Light Sensor",
#     kind=ProviderKind.LIGHT,
#     default_unit=PowerUnit.LUX,
# )

PROVIDER_DEFINITION_REGISTRY: Mapping[ProviderVendor, ProviderDefinition] = (
    ProviderDefinitionRegistry.all()
)


def resolve_sensor_type(vendor: ProviderVendor) -> SensorType | None:
    try:
        return SensorType(vendor.value)
    except ValueError:
        return None
