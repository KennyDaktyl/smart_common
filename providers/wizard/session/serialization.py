# smart_common/providers/wizard/session/serialization.py
from __future__ import annotations

from dataclasses import asdict
from datetime import datetime

from smart_common.providers.wizard.session.models import WizardSession


def serialize_session(session: WizardSession) -> dict:
    data = asdict(session)
    data["created_at"] = session.created_at.isoformat()
    data["updated_at"] = session.updated_at.isoformat()
    return data


def deserialize_session(data: dict) -> WizardSession:
    return WizardSession(
        **{
            **data,
            "created_at": datetime.fromisoformat(data["created_at"]),
            "updated_at": datetime.fromisoformat(data["updated_at"]),
        }
    )
