# smart_common/enums/provider.py
from enum import Enum


class ProviderType(str, Enum):
    API = "api"
    SENSOR = "sensor"
    VIRTUAL = "virtual"


class PowerUnit(str, Enum):
    WATT = "W"
    KILOWATT = "kW"


class ProviderKind(str, Enum):
    PV_INVERTER = "pv_inverter"
    