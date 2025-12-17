from enum import Enum


class PowerUnit(str, Enum):
    # --- Power / Energy ---
    WATT = "W"
    KILOWATT = "kW"

    WATT_HOUR = "Wh"
    KILOWATT_HOUR = "kWh"

    # --- Electrical ---
    VOLT = "V"
    AMPERE = "A"
    HERTZ = "Hz"

    # --- Environment ---
    CELSIUS = "C"
    FAHRENHEIT = "F"
    KELVIN = "K"

    PERCENT = "%"
    LUX = "lux"

    # --- Generic / virtual ---
    BOOLEAN = "bool"
    STATE = "state"
    NONE = "none"
