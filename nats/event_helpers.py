from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict
from uuid import uuid4

from smart_common.core.config import settings

EVENT_DATA_VERSION = "1"
DEFAULT_EVENT_SOURCE = "smart-common"


def stream_name() -> str:
    return settings.STREAM_NAME


def subject_for_entity(entity_id: str) -> str:
    """Return the stream-based subject for the given entity UUID."""
    normalized_id = _normalize_entity_id(entity_id)
    return f"{stream_name()}.{normalized_id}"


def ack_subject_for_entity(entity_id: str) -> str:
    """Append `.ack` to the entity-specific subject."""
    return f"{subject_for_entity(entity_id)}.ack"


def build_event_payload(
    *,
    event_type: str,
    entity_type: str,
    entity_id: str,
    data: Dict[str, Any],
    source: str | None = None,
    event_id: str | None = None,
    timestamp: str | None = None,
    data_version: str = EVENT_DATA_VERSION,
) -> Dict[str, Any]:
    """Construct the canonical event envelope."""
    normalized_source = source or DEFAULT_EVENT_SOURCE
    normalized_id = _normalize_entity_id(entity_id)
    payload_timestamp = timestamp or datetime.now(timezone.utc).isoformat()
    resolved_event_id = event_id or uuid4().hex

    return {
        "event_type": event_type,
        "event_id": resolved_event_id,
        "source": normalized_source,
        "entity_type": entity_type,
        "entity_id": normalized_id,
        "timestamp": payload_timestamp,
        "data_version": data_version,
        "data": data,
    }


def _normalize_entity_id(entity_id: str | Any) -> str:
    if isinstance(entity_id, str):
        return entity_id
    return str(entity_id)
