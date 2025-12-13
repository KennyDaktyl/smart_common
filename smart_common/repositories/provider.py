from __future__ import annotations

from smart_common.models.providers import Provider

from .base import BaseRepository


class ProviderRepository(BaseRepository[Provider]):
    model = Provider
