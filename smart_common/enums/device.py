from enum import Enum


class DeviceMode(str, Enum):
    MANUAL = "MANUAL"
    AUTO_POWER = "AUTO"
    SCHEDULE = "SCHEDULE"
