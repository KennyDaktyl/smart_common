from typing import Any, Dict, List, Optional, Union

from smart_common.enums.event import EventType
from smart_common.schemas.automation_rule import AutomationRuleGroup
from smart_common.schemas.base import APIModel


class BaseEvent(APIModel):
    event_type: EventType


class DeviceCreatedPayload(APIModel):
    device_id: int
    device_uuid: str
    device_number: int
    mode: str
    rated_power: Optional[float] = None
    threshold_value: Optional[float] = None
    threshold_kw: Optional[float] = None
    auto_rule: Optional[AutomationRuleGroup] = None
    scheduler_id: Optional[int] = None
    microcontroller_uuid: Optional[str] = None


class DeviceCreatedEvent(BaseEvent):
    payload: DeviceCreatedPayload


class DeviceUpdatedPayload(APIModel):
    device_number: int
    device_uuid: str
    device_id: int
    mode: str
    rated_power: Optional[float] = None
    threshold_kw: Optional[float] = None
    auto_rule: Optional[AutomationRuleGroup] = None
    scheduler_id: Optional[int] = None


class DeviceUpdatedEvent(BaseEvent):
    payload: DeviceUpdatedPayload


class PowerReadingPayload(APIModel):
    inverter_id: int
    power_kw: float
    device_ids: List[int]


class PowerReadingEvent(BaseEvent):
    payload: PowerReadingPayload


class DeviceCommandPayload(APIModel):
    command_id: str | None = None
    device_id: int
    device_uuid: str
    device_number: int
    mode: str
    command: str
    is_on: bool


class DeviceCommandEvent(BaseEvent):
    payload: DeviceCommandPayload


class MicrocontrollerCommandPayload(APIModel):
    command_id: str
    command: str
    config_json: Optional[Dict[str, Any]] = None
    hardware_config_json: Optional[Dict[str, Any]] = None
    env_file_content: Optional[str] = None


class MicrocontrollerCommandEvent(BaseEvent):
    payload: MicrocontrollerCommandPayload


class DeviceDeletePayload(APIModel):
    device_id: int
    device_uuid: str
    device_number: int


class DeviceDeletedEvent(BaseEvent):
    payload: DeviceDeletePayload


class DeviceEventUnion(BaseEvent):
    payload: Union[
        DeviceCreatedPayload,
        DeviceUpdatedPayload,
        PowerReadingPayload,
        DeviceCommandPayload,
        MicrocontrollerCommandPayload,
        DeviceDeletePayload,
    ]
