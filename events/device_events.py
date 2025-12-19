from typing import List, Optional, Union

from smart_common.enums.event import EventType
from smart_common.schemas.base import APIModel


class BaseEvent(APIModel):
    event_type: EventType


class DeviceCreatedPayload(APIModel):
    device_id: int
    device_number: int
    mode: str
    threshold_kw: Optional[float] = None
    inverter_serial: Optional[str] = None


class DeviceCreatedEvent(BaseEvent):
    payload: DeviceCreatedPayload


class DeviceUpdatedPayload(APIModel):
    device_id: int
    mode: str
    threshold_kw: Optional[float] = None


class DeviceUpdatedEvent(BaseEvent):
    payload: DeviceUpdatedPayload


class PowerReadingPayload(APIModel):
    inverter_id: int
    power_kw: float
    device_ids: List[int]


class PowerReadingEvent(BaseEvent):
    payload: PowerReadingPayload


class DeviceCommandPayload(APIModel):
    device_id: int
    command: str
    is_on: bool


class DeviceCommandEvent(BaseEvent):
    payload: DeviceCommandPayload


class DeviceDeletePayload(APIModel):
    device_id: int


class DeviceDeletedEvent(BaseEvent):
    payload: DeviceDeletePayload


class DeviceEventUnion(BaseEvent):
    payload: Union[
        DeviceCreatedPayload,
        DeviceUpdatedPayload,
        PowerReadingPayload,
        DeviceCommandPayload,
        DeviceDeletePayload,
    ]


class DeviceDeletePayload(APIModel):
    device_id: int


class DeviceDeletedEvent(BaseEvent):
    payload: DeviceDeletePayload
