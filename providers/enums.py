from enum import Enum


class ProviderType(str, Enum):
    API = "api"
    SENSOR = "sensor"
    MANUAL_OR_SCHEDULED = "manual_or_scheduled"


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
    # SMA = "sma"
    # SOLAREDGE = "solaredge"
    # FRONIUS = "fronius"
    # GROWATT = "growatt"
    # SUNGROW = "sungrow"
    # KOSTAL = "kostal"
    # VICTRON = "victron"
    # ENPHASE = "enphase"

    # # Sensors (hardware-only; must be validated against microcontroller capabilities)
    # DHT22 = "dht22"
    # BME280 = "bme280"
    # BH1750 = "bh1750"
