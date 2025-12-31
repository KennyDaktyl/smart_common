from __future__ import annotations

from smart_common.providers.enums import ProviderVendor
from smart_common.providers.wizard.base import ProviderWizard
from smart_common.providers.wizard.huawei.steps import (
    HuaweiAuthWizardStep,
    HuaweiStationWizardStep,
    HuaweiDeviceWizardStep,
    HuaweiDetailsWizardStep,
)


class HuaweiWizard(ProviderWizard):
    vendor = ProviderVendor.HUAWEI

    def __init__(self) -> None:
        super().__init__(
            steps=[
                HuaweiAuthWizardStep(),
                HuaweiStationWizardStep(),
                HuaweiDeviceWizardStep(),
                HuaweiDetailsWizardStep(),
            ]
        )
