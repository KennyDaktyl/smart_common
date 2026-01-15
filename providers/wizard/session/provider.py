# smart_common/providers/wizard/session/provider.py
from redis import Redis

from smart_common.providers.wizard.session.base import BaseWizardSessionStore
from smart_common.providers.wizard.session.in_memory import InMemoryWizardSessionStore
from smart_common.providers.wizard.session.redis_store import RedisWizardSessionStore
from smart_common.core.config import settings

_WIZARD_SESSION_STORE: BaseWizardSessionStore | None = None


def _create_store(redis: Redis | None = None) -> BaseWizardSessionStore:
    if settings.ENV in {"test", "development"} or redis is None:
        return InMemoryWizardSessionStore()

    return RedisWizardSessionStore(redis)


def get_wizard_session_store(redis: Redis | None = None) -> BaseWizardSessionStore:
    global _WIZARD_SESSION_STORE
    if _WIZARD_SESSION_STORE is None:
        _WIZARD_SESSION_STORE = _create_store(redis)
    return _WIZARD_SESSION_STORE
