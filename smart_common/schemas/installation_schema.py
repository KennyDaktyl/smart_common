from typing import List, Optional

from smart_common.schemas.base import APIModel, ORMModel
from smart_common.schemas.provider_schema import ProviderOut


class InstallationLite(ORMModel):
    id: int
    name: str


class InstallationBase(APIModel):
    name: str
    station_code: str
    station_addr: Optional[str] = None


class InstallationCreate(InstallationBase):
    pass


class InstallationUpdate(APIModel):
    name: Optional[str] = None
    station_addr: Optional[str] = None


class InstallationOut(InstallationBase, ORMModel):
    id: int
    user_id: int
    providers: List[ProviderOut] = []
