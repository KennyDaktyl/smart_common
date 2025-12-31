# smart_common/providers/wizard/session/models.py
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict

from smart_common.providers.enums import ProviderVendor


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class WizardSession:
    id: str
    vendor: ProviderVendor
    session_data: Dict[str, Any] = field(default_factory=dict)
    context: Dict[str, Any] = field(default_factory=dict)
    last_step: str | None = None
    created_at: datetime = field(default_factory=utcnow)
    updated_at: datetime = field(default_factory=utcnow)
