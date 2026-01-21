from typing import Any, Callable, Dict, Union

from pydantic import BaseModel

from smart_common.enums.event import EventType
from smart_common.nats.event_helpers import (
    ack_subject_for_entity,
    build_event_payload,
    subject_for_entity,
)


class EventDispatcher:
    """Helper that enforces the canonical event envelope for NATS messages."""

    def __init__(self, publisher: Any, *, default_source: str | None = None):
        self.publisher = publisher
        self.default_source = default_source

    def _serialize_data(self, data: Union[BaseModel, Dict[str, Any]]) -> Dict[str, Any]:
        if isinstance(data, BaseModel):
            return data.model_dump(mode="json")
        return dict(data)

    def _event_type_value(self, event_type: Union[EventType, str]) -> str:
        return event_type.value if isinstance(event_type, EventType) else str(event_type)

    async def publish_event(
        self,
        *,
        entity_type: str,
        entity_id: str,
        event_type: Union[EventType, str],
        data: Union[BaseModel, Dict[str, Any]],
        subject: str | None = None,
        source: str | None = None,
        context: Dict[str, Any] | None = None,
    ):
        """Publish a single event without waiting for acknowledgements."""
        payload = build_event_payload(
            event_type=self._event_type_value(event_type),
            entity_type=entity_type,
            entity_id=entity_id,
            data=self._serialize_data(data),
            source=source or self.default_source,
        )
        resolved_subject = subject or subject_for_entity(entity_id)
        return await self.publisher.publish(
            resolved_subject,
            payload,
            context=context or {},
        )

    async def publish_event_and_wait_for_ack(
        self,
        *,
        entity_type: str,
        entity_id: str,
        event_type: Union[EventType, str],
        data: Union[BaseModel, Dict[str, Any]],
        predicate: Callable[[dict], bool],
        timeout: float = 3.0,
        subject: str | None = None,
        ack_subject: str | None = None,
        source: str | None = None,
        context: Dict[str, Any] | None = None,
    ) -> dict:
        """Publish an event and wait for a matching acknowledgement."""
        resolved_subject = subject or subject_for_entity(entity_id)
        resolved_ack = ack_subject or ack_subject_for_entity(entity_id)
        payload = build_event_payload(
            event_type=self._event_type_value(event_type),
            entity_type=entity_type,
            entity_id=entity_id,
            data=self._serialize_data(data),
            source=source or self.default_source,
        )
        return await self.publisher.publish_and_wait_for_ack(
            subject=resolved_subject,
            ack_subject=resolved_ack,
            message=payload,
            predicate=predicate,
            timeout=timeout,
        )
