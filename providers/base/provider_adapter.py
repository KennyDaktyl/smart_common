from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Mapping

from smart_common.providers.base.adapter import BaseHttpAdapter
from smart_common.providers.enums import ProviderKind, ProviderType, ProviderVendor
from smart_common.schemas.normalized_measurement import NormalizedMeasurement


class BaseProviderAdapter(BaseHttpAdapter, ABC):
    """
    High-level provider adapter.

    Responsibilities:
    - expose provider capabilities (stations, devices, measurements)
    - normalize provider-specific payloads
    - raise ProviderError on failures

    IMPORTANT:
    - Base class MUST NOT implement business methods
    - Unsupported features should be expressed by NOT implementing them
    """

    provider_type: ProviderType | None = None
    vendor: ProviderVendor | None = None
    kind: ProviderKind | None = None

    def __init__(
        self,
        base_url: str,
        *,
        headers: Mapping[str, str] | None = None,
        timeout: float = 10.0,
        max_retries: int = 3,
    ) -> None:
        super().__init__(
            base_url,
            headers=headers,
            timeout=timeout,
            max_retries=max_retries,
        )

    # ------------------------------------------------------------------
    # Core capabilities (MUST be implemented if provider supports them)
    # ------------------------------------------------------------------

    @abstractmethod
    def list_stations(self) -> list[Mapping[str, Any]]:
        """Return normalized list of stations."""
        raise NotImplementedError

    @abstractmethod
    def list_devices(self, station_code: str) -> list[Mapping[str, Any]]:
        """Return normalized list of devices for a station."""
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Optional capabilities (override only if supported)
    # ------------------------------------------------------------------

    def get_current_power(self, device_id: str) -> float:
        raise NotImplementedError(f"{self.vendor} does not support power readings")

    def fetch_measurement(self) -> NormalizedMeasurement:
        raise NotImplementedError(f"{self.vendor} does not support measurements")

    # ------------------------------------------------------------------
    # Normalization hooks (optional)
    # ------------------------------------------------------------------

    def normalize_station(self, raw: Mapping[str, Any]) -> Mapping[str, Any]:
        return raw

    def normalize_device(self, raw: Mapping[str, Any]) -> Mapping[str, Any]:
        return raw
