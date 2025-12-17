from enum import Enum


class ProviderType(str, Enum):
    API = "api"
    SENSOR = "sensor"
    VIRTUAL = "virtual"


class ProviderKind(str, Enum):
    PV_INVERTER = "pv_inverter"
    TEMPERATURE = "temperature"
    HUMIDITY = "humidity"
    LIGHT = "light"
    POWER = "power"


class ProviderVendor(str, Enum):
    # API
    HUAWEI = "huawei"
    GOODWE = "goodwe"
    SIEMENS = "siemens"

    # Sensors
    DHT22 = "dht22"
    BME280 = "bme280"
    BH1750 = "bh1750"
