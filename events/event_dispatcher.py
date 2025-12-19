from typing import Any, Callable, Dict, Optional, Union

from pydantic import BaseModel

from smart_common.enums.event import EventType


class EventDispatcher:
    """Helper that enforces a unified event schema for NATS messages."""

    def __init__(self, publisher: Any):
        self.publisher = publisher

    def _build_message(
        self,
        *,
        event: Optional[Union[BaseModel, Dict[str, Any]]] = None,
        event_type: Optional[Union[EventType, str]] = None,
        payload: Optional[Union[BaseModel, Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        if event is not None:
            if isinstance(event, BaseModel):
                message = event.model_dump(mode="json")
            elif isinstance(event, dict):
                message = event
            else:
                raise TypeError("event must be a Pydantic model or dict")

            if "event_type" not in message or "payload" not in message:
                raise ValueError("event must contain 'event_type' and 'payload'")

            return message

        if event_type is None or payload is None:
            raise ValueError("event_type and payload required when event is not provided")

        if isinstance(payload, BaseModel):
            payload = payload.model_dump(mode="json")

        etype = event_type.value if isinstance(event_type, EventType) else str(event_type)

        return {"event_type": etype, "payload": payload}

    async def publish_event(
        self,
        subject: str,
        *,
        event: Optional[Union[BaseModel, Dict[str, Any]]] = None,
        event_type: Optional[Union[EventType, str]] = None,
        payload: Optional[Union[BaseModel, Dict[str, Any]]] = None,
    ):
        message = self._build_message(event=event, event_type=event_type, payload=payload)
        return await self.publisher.publish(subject, message)

    async def publish_event_and_wait_for_ack(
        self,
        subject: str,
        ack_subject: str,
        *,
        predicate: Callable[[dict], bool],
        timeout: float,
        event: Optional[Union[BaseModel, Dict[str, Any]]] = None,
        event_type: Optional[Union[EventType, str]] = None,
        payload: Optional[Union[BaseModel, Dict[str, Any]]] = None,
    ) -> dict:
        message = self._build_message(event=event, event_type=event_type, payload=payload)
        return await self.publisher.publish_and_wait_for_ack(
            subject=subject,
            ack_subject=ack_subject,
            message=message,
            predicate=predicate,
            timeout=timeout,
        )
