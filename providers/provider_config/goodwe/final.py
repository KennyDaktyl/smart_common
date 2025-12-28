from pydantic import Field
from smart_common.schemas.base import APIModel


class GoodWeProviderConfig(APIModel):
    powerstation_id: str = Field(
        ...,
        description="GoodWe PowerStationId (external provider ID)",
    )
    station_name: str | None = Field(
        None,
        description="Power station name",
    )
    address: str | None = Field(
        None,
        description="Installation address",
    )
    capacity_kw: float | None = Field(
        None,
        description="PV capacity in kWp",
    )
    battery_capacity_kwh: float | None = Field(
        None,
        description="Battery capacity in kWh",
    )
    powerstation_type: str | None = Field(
        None,
        description="Type of installation",
    )
    currency: str | None = Field(
        None,
        description="Currency used by GoodWe statistics",
    )
    inverter_sn: str | None = Field(
        None,
        description="Inverter serial number (optional)",
    )
    max_power_kw: float = Field(
        default=20.0,
        gt=0,
        description="Maximum inverter power in kW",
    )
