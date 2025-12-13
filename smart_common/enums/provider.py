# smart_common/enums/provider.py
from enum import Enum


class ProviderType(str, Enum):
    API = "api"
    SENSOR = "sensor"
    VIRTUAL = "virtual"


class PowerUnit(str, Enum):
    WATT = "W"
    KILOWATT = "kW"
    LUX = "lux"
    CELSIUS = "C"
    PERCENT = "%"


class ProviderKind(str, Enum):
    PV_INVERTER = "PV_INVERTER"
    

class ProviderVendor(str, Enum):
    HUAWEI = "huawei"
    GOODWE = "goodwe"
    SIEMENS = "siemens"
