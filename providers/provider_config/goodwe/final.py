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
    max_power_w: float = Field(
        default=10000.0,
        gt=0,
        description="Maximum inverter power in W",
    )
    min_power_w: float = Field(
        default=0.0,
        ge=0,
        description="Minimum inverter power in W",
    )
