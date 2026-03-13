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
    ENABLE_POLICY = "ENABLE_POLICY"
    DISABLE_POLICY = "DISABLE_POLICY"


class SchedulerControlMode(str, Enum):
    DIRECT = "DIRECT"
    POLICY = "POLICY"


class SchedulerPolicyType(str, Enum):
    TEMPERATURE_HYSTERESIS = "TEMPERATURE_HYSTERESIS"


class SchedulerPolicyEndBehavior(str, Enum):
    KEEP_CURRENT_STATE = "KEEP_CURRENT_STATE"
    FORCE_OFF = "FORCE_OFF"


class SchedulerCommandStatus(str, Enum):
    PENDING = "PENDING"
    SENT = "SENT"
    ACK_OK = "ACK_OK"
    ACK_FAIL = "ACK_FAIL"
    TIMEOUT = "TIMEOUT"
    CANCELLED = "CANCELLED"
