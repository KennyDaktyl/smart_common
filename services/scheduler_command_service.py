from __future__ import annotations

import logging

from smart_common.enums.device import DeviceMode
from smart_common.enums.event import EventType
from smart_common.enums.scheduler import SchedulerCommandAction
from smart_common.events.device_events import DeviceCommandPayload
from smart_common.nats.event_helpers import (
    ack_subject_for_entity,
    build_event_payload,
    subject_for_entity,
)
from smart_common.nats.publisher import publisher
from smart_common.schemas.scheduler_runtime import DispatchCommandEntry

logger = logging.getLogger(__name__)


class SchedulerCommandService:
    async def publish_command(self, *, command: DispatchCommandEntry) -> None:
        payload_data = DeviceCommandPayload(
            command_id=str(command.command_id),
            device_id=command.device_id,
            device_uuid=str(command.device_uuid),
            device_number=command.device_number,
            command="SET_STATE",
            mode=DeviceMode.SCHEDULE.value,
            is_on=command.action == SchedulerCommandAction.ON,
        ).model_dump(mode="json")

        subject = subject_for_entity(
            str(command.microcontroller_uuid),
            EventType.DEVICE_COMMAND.value,
        )
        ack_subject = ack_subject_for_entity(
            str(command.microcontroller_uuid),
            EventType.DEVICE_COMMAND.value,
        )

        event_payload = build_event_payload(
            subject=subject,
            event_type=EventType.DEVICE_COMMAND.value,
            entity_type=EventType.DEVICE_COMMAND.value,
            entity_id=str(command.microcontroller_uuid),
            data=payload_data,
            source="smart-schedulers",
        )
        event_payload["ack_subject"] = ack_subject

        await publisher.publish(
            subject=subject,
            payload=event_payload,
            context={
                "component": "scheduler-dispatcher",
                "device_id": command.device_id,
                "command_id": str(command.command_id),
                "action": command.action.value,
                "microcontroller_uuid": str(command.microcontroller_uuid),
            },
        )

        logger.info(
            "Scheduler command published | command_id=%s device_id=%s action=%s microcontroller_uuid=%s",
            command.command_id,
            command.device_id,
            command.action.value,
            command.microcontroller_uuid,
        )
