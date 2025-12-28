from __future__ import annotations

from pydantic import Field

from smart_common.providers.definitions.base import ProviderDefinition
from smart_common.schemas.base import APIModel


class HuaweiAuthStep(APIModel):
    username: str = Field(
        ...,
        title="Username",
        description="FusionSolar user login",
        min_length=1,
        json_schema_extra={
            "x-ui": {
                "widget": "text",
            }
        },
    )
    password: str = Field(
        ...,
        title="Password",
        description="FusionSolar password",
        min_length=1,
        json_schema_extra={
            "x-ui": {
                "widget": "password",
            }
        },
    )


class HuaweiStationStep(APIModel):
    station_code: str = Field(
        ...,
        title="Station",
        description="Selected station identifier",
        json_schema_extra={
            "x-ui": {
                "widget": "select",
                "options_key": "stations",
            }
        },
    )


class HuaweiDeviceStep(APIModel):
    station_code: str = Field(
        ...,
        title="Station",
        description="Station identifier (hidden)",
        json_schema_extra={
            "x-ui": {
                "widget": "text",
            }
        },
    )
    device_id: int = Field(
        ...,
        title="Device",
        description="Device identifier selected by user",
        json_schema_extra={
            "x-ui": {
                "widget": "select",
                "options_key": "devices",
            }
        },
    )


# class HuaweiCredentialsSchema(APIModel):
#     username: str
#     password: str


# class HuaweiProviderDefinition(ProviderDefinition):
#     credentials_schema = HuaweiCredentialsSchema
