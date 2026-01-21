# smart_common/providers/adapters/huawei.py
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping

from smart_common.enums.unit import PowerUnit
from smart_common.schemas.normalized_measurement import NormalizedMeasurement
from smart_common.providers.adapters.base import BaseProviderAdapter
from smart_common.providers.exceptions import ProviderError, ProviderFetchError
from smart_common.providers.enums import ProviderKind, ProviderType, ProviderVendor
from smart_common.providers.provider_config.config import provider_settings

logger = logging.getLogger(__name__)


class HuaweiProviderAdapter(BaseProviderAdapter):
    provider_type = ProviderType.API
    vendor = ProviderVendor.HUAWEI
    kind = ProviderKind.POWER

    def __init__(
        self,
        username: str,
        password: str,
        *,
        base_url: str | None = None,
        timeout: float | None = None,
        max_retries: int | None = None,
    ) -> None:
        super().__init__(
            base_url or provider_settings.HUAWEI_BASE_URL,
            headers={"Content-Type": "application/json"},
            timeout=timeout or provider_settings.HUAWEI_TIMEOUT,
            max_retries=max_retries or provider_settings.HUAWEI_MAX_RETRIES,
        )

        self.username = username
        self.password = password
        self._logged_in = False
        self._token_expires_at: datetime | None = None

    # ------------------------------------------------------------------
    # Login handling
    # ------------------------------------------------------------------

    def _is_expired(self) -> bool:
        return (
            self._token_expires_at is not None
            and datetime.now(timezone.utc) >= self._token_expires_at
        )

    def _ensure_login(self) -> None:
        if not self._logged_in or self._is_expired():
            logger.info("Huawei login required", extra=self._log_context())
            self._login()

    def _login(self) -> None:
        logger.info("Huawei login start", extra=self._log_context())

        payload = {
            "userName": self.username,
            "systemCode": self.password,
        }
        logger.info(
            "Huawei login request",
            extra={
                **self._log_context(),
                "endpoint": "login",
                "payload": payload,
            },
        )
        try:
            response = self._request(
                "POST",
                "login",
                json_data=payload,
            )
        except ProviderFetchError:
            raise
        except Exception as exc:
            logger.exception("Huawei login unexpected error")
            raise ProviderFetchError(
                "Huawei login failed",
                details={"error": str(exc)},
            ) from exc

        logger.info(
            "Huawei login response",
            extra={
                **self._log_context(),
                "status_code": response.status_code,
                "ok": response.ok,
                "body": response.text,
            },
        )

        if not response.ok:
            raise ProviderError(
                message="Huawei authentication failed",
                status_code=response.status_code,
                code="HUAWEI_AUTH_FAILED",
                details={"body": response.text},
            )

        result = response.json()
        if not result.get("success"):
            raise ProviderError(
                message="Huawei authentication rejected",
                status_code=401,
                code="HUAWEI_AUTH_REJECTED",
                details={
                    "message": result.get("message"),
                    "failCode": result.get("failCode"),
                },
            )

        xsrf = self.session.cookies.get("XSRF-TOKEN")
        if not xsrf:
            raise ProviderError(
                message="Huawei login missing XSRF token",
                status_code=502,
                code="HUAWEI_XSRF_MISSING",
            )

        self.session.headers["XSRF-TOKEN"] = xsrf
        self._logged_in = True
        self._token_expires_at = datetime.now(timezone.utc) + timedelta(minutes=25)

        logger.info("Huawei login OK", extra=self._log_context())

    # ------------------------------------------------------------------
    # Internal POST helper (Huawei-specific)
    # ------------------------------------------------------------------

    def _post(self, endpoint: str, payload: dict | None = None) -> dict:
        self._ensure_login()
        safe_payload = payload or {}

        logger.info(
            "Huawei API request",
            extra={
                **self._log_context(),
                "endpoint": endpoint,
                "payload": safe_payload,
            },
        )

        response = self._request(
            "POST",
            endpoint,
            json_data=safe_payload,
        )

        logger.info(
            "Huawei API response",
            extra={
                **self._log_context(),
                "endpoint": endpoint,
                "status_code": response.status_code,
                "ok": response.ok,
                "body": response.text,
            },
        )

        if response.status_code == 401:
            logger.warning("Huawei 401 → re-login")
            self._login()
            response = self._request("POST", endpoint, json_data=payload or {})

            logger.info(
                "Huawei API response (after relogin)",
                extra={
                    **self._log_context(),
                    "endpoint": endpoint,
                    "status_code": response.status_code,
                    "ok": response.ok,
                    "body": response.text,
                },
            )

        result = response.json()

        if (
            result.get("message") == "USER_MUST_RELOGIN"
            or result.get("failCode") == 20010
        ):
            logger.warning("Huawei USER_MUST_RELOGIN → re-login")
            self._login()
            response = self._request("POST", endpoint, json_data=payload or {})
            result = response.json()

            logger.info(
                "Huawei API response (USER_MUST_RELOGIN)",
                extra={
                    **self._log_context(),
                    "endpoint": endpoint,
                    "status_code": response.status_code,
                    "body": response.text,
                },
            )

        if not result.get("success", False):
            raise ProviderError(
                message="Huawei API error",
                status_code=502,
                code="HUAWEI_API_ERROR",
                details={
                    "message": result.get("message"),
                    "failCode": result.get("failCode"),
                },
            )

        self._token_expires_at = datetime.now(timezone.utc) + timedelta(minutes=25)
        return result

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def list_stations(self) -> list[Mapping[str, Any]]:
        logger.info("Huawei → list stations", extra=self._log_context())

        result = self._post("getStationList")
        stations = result.get("data", [])

        logger.info(
            "Huawei stations fetched",
            extra={**self._log_context(), "count": len(stations)},
        )

        return [self._normalize_station(s) for s in stations]

    def list_devices(self, station_code: str) -> list[Mapping[str, Any]]:
        logger.info(
            "Huawei → list devices",
            extra={**self._log_context(), "station_code": station_code},
        )

        payload = {"stationCodes": station_code}
        result = self._post("getDevList", payload)
        devices = result.get("data", [])

        inverters = [d for d in devices if d.get("devTypeId") == 1]

        logger.info(
            "Huawei inverters fetched",
            extra={
                **self._log_context(),
                "station_code": station_code,
                "count": len(inverters),
            },
        )

        return [self._normalize_device(d) for d in inverters]

    def get_production(self, device_id: str) -> dict:
        payload = {"devTypeId": "1", "devIds": device_id}
        logger.info(
            "Huawei → get production",
            extra={**self._log_context(), "payload": payload},
        )

        result = self._post("getDevRealKpi", payload)
        logger.info(
            "Huawei API response",
            extra={
                **self._log_context(),
                "endpoint": "getDevRealKpi",
                "status_code": result.get("status_code"),
                "body": result.get("body"),
            },
        )
        return result.get("data", [])

    def get_current_power(self, device_id: str) -> float:
        logger.info(
            "Huawei fetch current power start",
            extra=self._log_context(device_id=device_id),
        )
        payload = self.get_production(device_id)
        data = payload[0] if isinstance(payload, list) and payload else payload
        if not isinstance(data, Mapping):
            raise ProviderError(
                message="Huawei getDevRealKpi returned unexpected payload",
                details={"payload": payload},
            )

        power_value = self._extract_power_value(data)
        if power_value is None:
            raise ProviderError(
                message="Huawei getDevRealKpi missing power value",
                details={"payload": payload},
            )

        logger.info(
            "Huawei current power value parsed",
            extra=self._log_context(device_id=device_id, value=power_value),
        )
        return power_value

    def _extract_power_value(self, payload: Mapping[str, Any]) -> float | None:
        data_item_map = payload.get("dataItemMap")
        if isinstance(data_item_map, Mapping):
            value = data_item_map.get("active_power")
            if value is not None:
                try:
                    return float(value)
                except (TypeError, ValueError):
                    return None
        active_power = payload.get("active_power")
        if active_power is None:
            return None
        try:
            return float(active_power)
        except (TypeError, ValueError):
            return None

    # ------------------------------------------------------------------
    # Normalization
    # ------------------------------------------------------------------

    def _normalize_station(self, raw: Mapping[str, Any]) -> Mapping[str, Any]:
        return {
            "station_code": raw.get("stationCode"),
            "name": raw.get("stationName"),
            "capacity_kw": raw.get("capacity"),
            "grid_connected_time": raw.get("gridConnectedTime"),
            "raw": dict(raw),
        }

    def _normalize_device(self, raw: Mapping[str, Any]) -> Mapping[str, Any]:
        return {
            "device_id": raw.get("id"),
            "name": raw.get("devName"),
            "station_code": raw.get("stationCode"),
            "device_type": raw.get("devTypeId"),
            "model": raw.get("model"),
            "inv_type": raw.get("invType"),
            "latitude": raw.get("latitude"),
            "longitude": raw.get("longitude"),
            "optimizer_count": raw.get("optimizerNumber"),
            "software_version": raw.get("softwareVersion"),
            "raw": dict(raw),
        }

    def fetch_measurement(self) -> NormalizedMeasurement:
        logger.info("Huawei fetching measurement", extra=self._log_context())
        device_id = getattr(self, "provider_external_id", None)
        if not device_id:
            raise ProviderError(
                message="Huawei adapter missing device identifier",
                details={"vendor": self.vendor.value},
            )

        value = self.get_current_power(device_id)
        measured_at = datetime.now(timezone.utc)

        logger.info(
            "Huawei measurement ready",
            extra=self._log_context(device_id=device_id, value=value),
        )
        return NormalizedMeasurement(
            provider_id=getattr(self, "provider_id", 0),
            value=value,
            unit=PowerUnit.WATT.value,
            measured_at=measured_at,
            metadata={"device_id": device_id},
        )
