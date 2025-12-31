# smart_common/providers/wizard/factory.py
from __future__ import annotations

from typing import Mapping

from smart_common.providers.definitions.base import ProviderDefinition
from smart_common.providers.enums import ProviderVendor
from smart_common.providers.wizard.base import ProviderWizard
from smart_common.providers.wizard.exceptions import WizardNotConfiguredError


class ProviderWizardFactory:
    def __init__(
        self,
        definitions: Mapping[ProviderVendor, ProviderDefinition],
    ) -> None:
        self._definitions = definitions

    def create(self, vendor: ProviderVendor) -> ProviderWizard:
        definition = self._definitions.get(vendor)
        if not definition or not definition.wizard_cls:
            raise WizardNotConfiguredError(
                f"No wizard registered for provider {vendor.value}"
            )

        return definition.wizard_cls()
