import logging
from typing import Any, Callable, Dict, Union

from pydantic import BaseModel

from smart_common.enums.event import EventType
from smart_common.nats.event_helpers import (
    ack_subject_for_entity,
    build_event_payload,
    subject_for_entity,
)

logger = logging.getLogger(__name__)


class EventDispatcher:
    """
    Helper that enforces the canonical event envelope for NATS messages.

    IMPORTANT:
    - ack_subject MUST be included in payload
    - backend waits on this subject explicitly
    """

    def __init__(self, publisher: Any, *, default_source: str | None = None):
        self.publisher = publisher
        self.default_source = default_source

    def _serialize_data(self, data: Union[BaseModel, Dict[str, Any]]) -> Dict[str, Any]:
        if isinstance(data, BaseModel):
            return data.model_dump(mode="json")
        return dict(data)

    def _event_type_value(self, event_type: Union[EventType, str]) -> str:
        return (
            event_type.value if isinstance(event_type, EventType) else str(event_type)
        )

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
        resolved_subject = subject or subject_for_entity(entity_id)

        payload = build_event_payload(
            subject=resolved_subject,
            event_type=self._event_type_value(event_type),
            entity_type=entity_type,
            entity_id=entity_id,
            data=self._serialize_data(data),
            source=source or self.default_source,
        )

        logger.info(
            "NATS PUBLISH → subject=%s event_type=%s entity_id=%s",
            resolved_subject,
            event_type,
            entity_id,
        )
        logger.debug("NATS PAYLOAD → %s", payload)

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
        """
        Publish an event and wait for a matching acknowledgement.

        Contract:
        - Event payload MUST contain `ack_subject`
        - Agent publishes ACK to that subject
        """

        logger.info("Publish event and wait for ACK")

        resolved_subject = subject or subject_for_entity(entity_id)
        resolved_ack = ack_subject or ack_subject_for_entity(entity_id)

        payload = build_event_payload(
            subject=resolved_subject,
            event_type=self._event_type_value(event_type),
            entity_type=entity_type,
            entity_id=entity_id,
            data=self._serialize_data(data),
            source=source or self.default_source,
        )

        # 🔥 KLUCZOWA POPRAWKA — ACK SUBJECT W KONTRAKCIE
        payload["ack_subject"] = resolved_ack

        logger.info(
            "NATS PUBLISH → subject=%s ack_subject=%s event_type=%s entity_id=%s",
            resolved_subject,
            resolved_ack,
            event_type,
            entity_id,
        )
        logger.debug("NATS PAYLOAD → %s", payload)

        try:
            result = await self.publisher.publish_and_wait_for_ack(
                subject=resolved_subject,
                ack_subject=resolved_ack,
                message=payload,
                predicate=predicate,
                timeout=timeout,
            )

            logger.info("NATS ACK RECEIVED → %s", result)
            return result

        except Exception:
            logger.exception("NATS ACK TIMEOUT / ERROR")
            raise
