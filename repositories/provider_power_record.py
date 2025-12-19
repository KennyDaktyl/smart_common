from __future__ import annotations

from smart_common.models.provider_power_record import ProviderPowerRecord
from smart_common.repositories.base import BaseRepository


class ProviderPowerRecordRepository(BaseRepository[ProviderPowerRecord]):
    model = ProviderPowerRecord
