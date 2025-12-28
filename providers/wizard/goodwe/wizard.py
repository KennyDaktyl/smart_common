from __future__ import annotations

from smart_common.providers.enums import ProviderVendor
from smart_common.providers.wizard.base import ProviderWizard
from smart_common.providers.wizard.goodwe.steps import (
    GoodWeAuthWizardStep,
    GoodWeDetailsWizardStep,
    GoodWeFinalizeWizardStep,
)


class GoodWeWizard(ProviderWizard):
    vendor = ProviderVendor.GOODWE

    def __init__(self) -> None:
        super().__init__(
            steps=[
                GoodWeAuthWizardStep(),
                GoodWeFinalizeWizardStep(),
                GoodWeDetailsWizardStep(),
            ]
        )
