from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, Mapping

import requests
from requests import Session

from smart_common.providers.enums import ProviderKind, ProviderType, ProviderVendor
from smart_common.providers.exceptions import ProviderFetchError

logger = logging.getLogger(__name__)


class BaseHttpAdapter:
    """
    Low-level HTTP helper for provider integrations.

    Handles:
        - base URL construction
        - retries + timeouts
        - connection/session management
    """

    def __init__(
        self,
        base_url: str,
        *,
        headers: Mapping[str, str] | None = None,
        timeout: float = 10.0,
        max_retries: int = 3,
    ) -> None:
        if not base_url:
            raise ValueError("base_url is required")

        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max(1, max_retries)

        self.session: Session = requests.Session()
        self.session.headers.update(
            {
                "Accept": "application/json",
                **(headers or {}),
            }
        )

    def _request(
        self,
        method: str,
        path: str,
        *,
        json_data: dict | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> requests.Response:
        url = self._url(path)
        last_exc: Exception | None = None

        for attempt in range(1, self.max_retries + 1):
            try:
                logger.debug(
                    "HTTP request attempt %s/%s",
                    attempt,
                    self.max_retries,
                    extra={
                        "method": method,
                        "url": url,
                    },
                )
                request_headers = (
                    {**self.session.headers, **(headers or {})}
                    if headers
                    else self.session.headers
                )
                return self.session.request(
                    method,
                    url,
                    json=json_data,
                    timeout=self.timeout,
                    headers=request_headers,
                )

            except requests.Timeout as exc:
                last_exc = exc
                logger.warning(
                    "HTTP timeout",
                    extra={"url": url, "attempt": attempt},
                )
            except requests.RequestException as exc:
                last_exc = exc
                logger.warning(
                    "HTTP request error",
                    extra={"url": url, "attempt": attempt, "error": str(exc)},
                )

        logger.error(
            "HTTP request failed after retries",
            extra={"url": url, "retries": self.max_retries},
        )
        raise ProviderFetchError(
            "HTTP request failed after retries",
            details={"error": str(last_exc)},
        )

    def _url(self, path: str) -> str:
        return f"{self.base_url}/{path.lstrip('/')}"

    def close(self) -> None:
        self.session.close()


class BaseProviderAdapter(BaseHttpAdapter, ABC):
    """
    High-level provider adapter.

    Responsibilities:
        - expose provider capabilities (stations, devices, measurements)
        - normalize provider-specific payloads
        - raise ProviderError on failures
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

    @abstractmethod
    def list_stations(self) -> list[Mapping[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def list_devices(self, station_code: str) -> list[Mapping[str, Any]]:
        raise NotImplementedError

    def get_current_power(self, device_id: str) -> float:
        raise NotImplementedError(f"{self.vendor} does not support power readings")

    def fetch_measurement(self) -> Any:  # type: ignore[override]
        raise NotImplementedError(f"{self.vendor} does not support measurements")

    def normalize_station(self, raw: Mapping[str, Any]) -> Mapping[str, Any]:
        return raw

    def normalize_device(self, raw: Mapping[str, Any]) -> Mapping[str, Any]:
        return raw

    def _log_context(
        self,
        *,
        task_name: str | None = None,
        **overrides: Any,
    ) -> dict[str, Any]:
        context: dict[str, Any] = {
            "provider_id": getattr(self, "provider_id", None),
            "vendor": self.vendor.value if self.vendor else None,
        }
        poll_id = getattr(self, "poll_id", None)
        if poll_id:
            context["poll_id"] = poll_id
        name = task_name or getattr(self, "task_name", None)
        if name:
            context["taskName"] = name
        context.update(overrides)
        return context
