# smart_common/providers/wizard/session/in_memory.py
from __future__ import annotations

from threading import Lock
from typing import Dict
from uuid import uuid4

from smart_common.providers.enums import ProviderVendor
from smart_common.providers.wizard.session.base import BaseWizardSessionStore
from smart_common.providers.wizard.session.models import WizardSession, utcnow


class InMemoryWizardSessionStore(BaseWizardSessionStore):
    def __init__(self) -> None:
        self._sessions: Dict[str, WizardSession] = {}
        self._lock = Lock()

    def create(self, vendor: ProviderVendor) -> WizardSession:
        with self._lock:
            session_id = uuid4().hex
            session = WizardSession(
                id=session_id,
                vendor=vendor,
                context={"wizard_session_id": session_id},
            )
            self._sessions[session_id] = session
            return session

    def get(self, session_id: str) -> WizardSession | None:
        with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                return None
            session.updated_at = utcnow()
            return session

    def persist(self, session: WizardSession) -> None:
        with self._lock:
            session.updated_at = utcnow()
            self._sessions[session.id] = session

    def delete(self, session_id: str) -> None:
        with self._lock:
            self._sessions.pop(session_id, None)
