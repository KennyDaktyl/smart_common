from pydantic import Field
from smart_common.schemas.base import APIModel


class HuaweiProviderConfig(APIModel):
    station_code: str
    inverter_id: int = Field(..., description="Huawei inverter numeric id")

    name: str
    model: str | None = None
    inv_type: str | None = None

    latitude: float | None = None
    longitude: float | None = None

    software_version: str | None = None
    optimizer_count: int | None = None

    max_power_kw: float = Field(default=20.0, gt=0)
    min_power_kw: float = Field(default=0.0, ge=0)
