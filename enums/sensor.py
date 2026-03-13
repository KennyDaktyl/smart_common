from enum import Enum


class SensorType(str, Enum):
    DHT22 = "dht22"
    BME280 = "bme280"
    BH1750 = "bh1750"
    DS18B20 = "ds18b20"
