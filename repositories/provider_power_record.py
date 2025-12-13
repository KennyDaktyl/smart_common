from __future__ import annotations

from models.provider_power_record import ProviderPowerRecord

from .base import BaseRepository


class ProviderPowerRecordRepository(BaseRepository[ProviderPowerRecord]):
    model = ProviderPowerRecord
