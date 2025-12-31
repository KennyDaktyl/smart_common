from __future__ import annotations

from pydantic import Field

from smart_common.schemas.base import APIModel


class GoodWeAuthStep(APIModel):
    username: str = Field(
        ...,
        title="Username",
        description="GoodWe / SEMS login",
        json_schema_extra={"x-ui": {"widget": "text"}},
    )
    password: str = Field(
        ...,
        title="Password",
        description="GoodWe / SEMS password",
        json_schema_extra={"x-ui": {"widget": "password"}},
    )


class GoodWePowerStationStep(APIModel):
    powerstation_id: str = Field(
        ...,
        title="Power Station",
        description="Select GoodWe PowerStation ID",
        json_schema_extra={
            "x-ui": {
                "widget": "select",
                "options_key": "powerstation_id",
            }
        },
    )


class GoodWeDetailsForm(APIModel):
    powerstation_id: str = Field(
        ...,
        title="Power Station ID",
        description="GoodWe PowerStation ID",
        json_schema_extra={
            "x-ui": {
                "widget": "text",
                "readonly": True,
            }
        },
    )

    station_name: str | None = Field(
        None,
        title="Station name",
        description="Power station name",
        json_schema_extra={"x-ui": {"widget": "text"}},
    )

    address: str | None = Field(
        None,
        title="Address",
        description="Installation address",
        json_schema_extra={"x-ui": {"widget": "text"}},
    )

    capacity_kw: float | None = Field(
        None,
        title="PV capacity (kWp)",
        description="PV capacity reported by GoodWe",
        json_schema_extra={"x-ui": {"widget": "number"}},
    )

    battery_capacity_kwh: float | None = Field(
        None,
        title="Battery capacity (kWh)",
        description="Battery capacity reported by GoodWe",
        json_schema_extra={"x-ui": {"widget": "number"}},
    )

    powerstation_type: str | None = Field(
        None,
        title="Installation type",
        description="Installation type reported by GoodWe",
        json_schema_extra={"x-ui": {"widget": "text"}},
    )

    currency: str | None = Field(
        None,
        title="Currency",
        description="Currency used by GoodWe statistics",
        json_schema_extra={"x-ui": {"widget": "text"}},
    )

    max_power_kw: float = Field(
        20.0,
        gt=0,
        title="Max inverter power (kW)",
        description="Maximum inverter power",
        json_schema_extra={"x-ui": {"widget": "number"}},
    )


class GoodWeDetailsSummary(APIModel):
    powerstation_id: str
    station_name: str | None
    address: str | None
    capacity_kw: float | None
    battery_capacity_kwh: float | None
    powerstation_type: str | None
    currency: str | None
    max_power_kw: float = 20.0
