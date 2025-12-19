# providers/base.py
from __future__ import annotations

from abc import ABC, abstractmethod

from smart_common.schemas.provider_schema import ProviderBase

from .models import NormalizedMeasurement


class BaseProviderAdapter(ABC):
    """Async base class for any provider adapter implementation."""

    def __init__(self, config: ProviderBase) -> None:
        self.config = config

    @abstractmethod
    async def validate_config(self) -> None:
        """Validate the provided configuration before any work."""

    @abstractmethod
    async def fetch_measurement(self) -> NormalizedMeasurement:
        """Fetch a normalized measurement for the underlying provider."""
