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
    """Technical step – no user input."""

    powerstation_id: str = Field(
        ...,
        title="Power Station",
        json_schema_extra={
            "x-ui": {
                "widget": "select",
                "options_key": "powerstation_id",
                "readonly": True,
            }
        },
    )


class GoodWeFinalizeStep(APIModel):
    """
    Final technical step – no user input.
    Exists only to satisfy wizard contract.
    """

    pass


class GoodWeFinalSummary(APIModel):
    powerstation_id: str = Field(..., description="GoodWe PowerStationId")
    station_name: str | None = Field(None, description="Station name")
    address: str | None = Field(None, description="Installation address")
    capacity_kwp: float | None = Field(None, description="PV capacity (kWp)")
    battery_capacity_kwh: float | None = Field(
        None, description="Battery capacity (kWh)"
    )
    powerstation_type: str | None = Field(None, description="Installation type")

    currency: str | None = Field(None, description="Currency")
