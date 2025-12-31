# smart_common/providers/wizard/session/base.py
from __future__ import annotations

from abc import ABC, abstractmethod

from smart_common.providers.enums import ProviderVendor
from smart_common.providers.wizard.session.models import WizardSession


class BaseWizardSessionStore(ABC):

    @abstractmethod
    def create(self, vendor: ProviderVendor) -> WizardSession:
        ...

    @abstractmethod
    def get(self, session_id: str) -> WizardSession | None:
        ...

    @abstractmethod
    def persist(self, session: WizardSession) -> None:
        ...

    @abstractmethod
    def delete(self, session_id: str) -> None:
        ...
