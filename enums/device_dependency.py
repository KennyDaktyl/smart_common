from enum import Enum


class DeviceDependencyAction(str, Enum):
    NONE = "NONE"
    ON = "ON"
    OFF = "OFF"
