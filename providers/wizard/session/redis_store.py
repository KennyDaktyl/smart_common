# smart_common/providers/wizard/session/redis_store.py
from __future__ import annotations

import json
from uuid import uuid4

from redis import Redis

from smart_common.providers.enums import ProviderVendor
from smart_common.providers.wizard.session.base import BaseWizardSessionStore
from smart_common.providers.wizard.session.models import WizardSession, utcnow
from smart_common.providers.wizard.session.serialization import (
    serialize_session,
    deserialize_session,
)


class RedisWizardSessionStore(BaseWizardSessionStore):
    def __init__(self, redis: Redis, ttl_seconds: int = 600) -> None:
        self.redis = redis
        self.ttl = ttl_seconds

    def _key(self, session_id: str) -> str:
        return f"wizard:session:{session_id}"

    def create(self, vendor: ProviderVendor) -> WizardSession:
        session_id = uuid4().hex
        session = WizardSession(
            id=session_id,
            vendor=vendor,
            context={"wizard_session_id": session_id},
        )
        self.persist(session)
        return session

    def get(self, session_id: str) -> WizardSession | None:
        raw = self.redis.get(self._key(session_id))
        if not raw:
            return None

        session = deserialize_session(json.loads(raw))
        session.updated_at = utcnow()
        self.persist(session)
        return session

    def persist(self, session: WizardSession) -> None:
        session.updated_at = utcnow()
        self.redis.setex(
            self._key(session.id),
            self.ttl,
            json.dumps(serialize_session(session)),
        )

    def delete(self, session_id: str) -> None:
        self.redis.delete(self._key(session_id))
