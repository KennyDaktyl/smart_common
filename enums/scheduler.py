from enum import Enum


class SchedulerDayOfWeek(str, Enum):
    MONDAY = "MONDAY"
    TUESDAY = "TUESDAY"
    WEDNESDAY = "WEDNESDAY"
    THURSDAY = "THURSDAY"
    FRIDAY = "FRIDAY"
    SATURDAY = "SATURDAY"
    SUNDAY = "SUNDAY"


class SchedulerCommandAction(str, Enum):
    ON = "ON"
    OFF = "OFF"


class SchedulerCommandStatus(str, Enum):
    PENDING = "PENDING"
    SENT = "SENT"
    ACK_OK = "ACK_OK"
    ACK_FAIL = "ACK_FAIL"
    TIMEOUT = "TIMEOUT"
    CANCELLED = "CANCELLED"
