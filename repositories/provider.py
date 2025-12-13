from __future__ import annotations

from models.providers import Provider

from .base import BaseRepository


class ProviderRepository(BaseRepository[Provider]):
    model = Provider
