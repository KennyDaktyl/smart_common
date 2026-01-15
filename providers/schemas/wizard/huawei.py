from __future__ import annotations

from pydantic import ConfigDict, Field

from smart_common.schemas.base import APIModel


# ------------------------------------------------------------
# AUTH
# ------------------------------------------------------------


class HuaweiAuthForm(APIModel):
    username: str = Field(
        ...,
        title="Username",
        description="FusionSolar user login",
        min_length=1,
        json_schema_extra={"x-ui": {"widget": "text", "required": True}},
    )
    password: str = Field(
        ...,
        title="Password",
        description="FusionSolar password",
        min_length=1,
        json_schema_extra={"x-ui": {"widget": "password", "required": True}},
    )


# ------------------------------------------------------------
# STATION
# ------------------------------------------------------------


class HuaweiStationForm(APIModel):
    model_config = ConfigDict(extra="ignore")
    station_code: str = Field(
        ...,
        title="Station",
        description="Selected station identifier",
        json_schema_extra={
            "x-ui": {"widget": "select", "options_key": "stations", "required": True}
        },
    )


# ------------------------------------------------------------
# DEVICE SELECT
# ------------------------------------------------------------


class HuaweiDeviceSelectForm(APIModel):
    model_config = ConfigDict(extra="ignore")
    device_id: int = Field(
        ...,
        title="Device",
        description="Huawei inverter device",
        json_schema_extra={
            "x-ui": {"widget": "select", "options_key": "devices", "required": True}
        },
    )


# ------------------------------------------------------------
# DETAILS FORM (editable)
# ------------------------------------------------------------


class HuaweiDetailsForm(APIModel):
    model_config = ConfigDict(extra="ignore")
    station_code: str = Field(
        ...,
        title="Station code",
        json_schema_extra={
            "x-ui": {"widget": "text", "readonly": True, "required": True}
        },
    )

    inverter_id: int = Field(
        ...,
        title="Inverter ID",
        json_schema_extra={
            "x-ui": {"widget": "text", "readonly": True, "required": True}
        },
    )

    name: str | None = Field(
        None,
        title="Inverter name",
        json_schema_extra={"x-ui": {"widget": "text", "required": True}},
    )

    model: str | None = Field(
        None,
        title="Inverter model",
        json_schema_extra={"x-ui": {"widget": "text", "readonly": True}},
    )

    inv_type: str | None = Field(
        None,
        title="Inverter type",
        json_schema_extra={"x-ui": {"widget": "text", "readonly": True}},
    )

    latitude: float | None = Field(
        None,
        title="Latitude",
        json_schema_extra={"x-ui": {"widget": "number", "readonly": True}},
    )

    longitude: float | None = Field(
        None,
        title="Longitude",
        json_schema_extra={"x-ui": {"widget": "number", "readonly": True}},
    )

    software_version: str | None = Field(
        None,
        title="Software version",
        json_schema_extra={"x-ui": {"widget": "text", "readonly": True}},
    )

    optimizer_count: int | None = Field(
        None,
        title="Optimizer count",
        json_schema_extra={"x-ui": {"widget": "number", "readonly": True}},
    )

    max_power_kw: float = Field(
        10.0,
        gt=0,
        title="Max power (kW)",
        json_schema_extra={"x-ui": {"widget": "number", "required": True}},
    )

    min_power_kw: float = Field(
        0.0,
        ge=0,
        title="Min power (kW)",
        json_schema_extra={"x-ui": {"widget": "number", "required": True}},
    )


# ------------------------------------------------------------
# DETAILS SUMMARY (API → prefill)
# ------------------------------------------------------------


class HuaweiDetailsSummary(APIModel):
    station_code: str
    inverter_id: int
    name: str
    model: str | None
    inv_type: str
    latitude: float | None
    longitude: float | None
    software_version: str | None
    optimizer_count: int | None
    max_power_kw: float = 10.0
    min_power_kw: float = 0.0
