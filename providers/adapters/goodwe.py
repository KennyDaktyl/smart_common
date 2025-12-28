from __future__ import annotations

import json
import logging
from typing import Any, Mapping

from smart_common.providers.adapters.base import BaseProviderAdapter
from smart_common.providers.enums import ProviderKind, ProviderType, ProviderVendor
from smart_common.providers.exceptions import ProviderError, ProviderFetchError
from smart_common.providers.provider_config.goodwe import goodwe_integration_settings

logger = logging.getLogger(__name__)


class GoodWeProviderAdapter(BaseProviderAdapter):
    provider_type = ProviderType.API
    vendor = ProviderVendor.GOODWE
    kind = ProviderKind.POWER

    SEMS_VER = "v2.1.0"

    def __init__(self, username: str, password: str) -> None:
        super().__init__(
            base_url="https://www.semsportal.com",
            timeout=goodwe_integration_settings.GOODWE_TIMEOUT,
            max_retries=goodwe_integration_settings.GOODWE_MAX_RETRIES,
        )
        self.username = username
        self.password = password

        self._logged_in: bool = False
        self._token_ctx: dict[str, Any] | None = None
        self._powerstation_id: str | None = None
        self._external_id: str | None = None

    # ------------------------------------------------------------------
    # PUBLIC API (used by wizard / services)
    # ------------------------------------------------------------------

    def authenticate(self) -> None:
        """Public auth entrypoint"""
        self._authenticate()

    def get_powerstation_id(self) -> str:
        """
        Step 1 domain method:
        returns GoodWe PowerStationId for logged-in user
        """
        self._authenticate()

        if self._external_id:
            return self._external_id

        station_id = self._post(
            "/PowerStation/GetPowerStationIdByOwner",
            payload={},
        )

        if not isinstance(station_id, str):
            raise ProviderError(
                message="Invalid PowerStationId returned by GoodWe",
                details={"data": station_id},
            )

        self._external_id = station_id
        return station_id

    def get_powerstation_detail(self, powerstation_id: str) -> dict[str, Any]:
        """Full plant details (info + kpi)"""
        response = self._post(
            "/api/v3/PowerStation/GetPlantDetailByPowerstationId",
            payload={"PowerStationId": powerstation_id},
        )

        logger.info("GoodWe plant detail response: %s", response)
        if not isinstance(response, dict):
            raise ProviderError("Invalid plant detail payload from GoodWe")

        return response

    def get_current_power(self, device_id: str | None = None) -> float:
        """
        Current power in **W**
        """
        powerstation_id = self.get_powerstation_id()

        data = self._post(
            "/api/v2/PowerStation/GetPowerflow",
            payload={"uid": powerstation_id},
        )

        power = data.get("power")
        if power is None:
            raise ProviderError("Missing power value in GoodWe GetPowerflow")

        return float(power)

    # ------------------------------------------------------------------
    # REQUIRED BY BASE
    # ------------------------------------------------------------------

    def list_stations(self) -> list[Mapping[str, Any]]:
        station_id = self.get_powerstation_id()
        return [
            {
                "station_id": station_id,
                "external_id": station_id,
            }
        ]

    def list_devices(self, station_code: str) -> list[Mapping[str, Any]]:
        # GoodWe = 1 logical device per plant
        return [
            {
                "device_id": station_code,
                "external_id": station_code,
            }
        ]

    # ------------------------------------------------------------------
    # INTERNAL
    # ------------------------------------------------------------------

    def _authenticate(self) -> None:
        if self._logged_in:
            return

        response = self._request(
            "POST",
            "/api/v2/Common/CrossLogin",
            json_data={
                "account": self.username,
                "pwd": self.password,
                "agreement_agreement": 0,
                "is_local": False,
            },
            headers={
                "Content-Type": "application/json;charset=UTF-8",
                "Accept": "application/json, text/plain, */*",
                "User-Agent": "Mozilla/5.0",
                "Token": json.dumps(
                    {
                        "client": "web",
                        "language": "zh_CN",
                        "version": self.SEMS_VER,
                    },
                    separators=(",", ":"),
                ),
            },
        )

        try:
            payload = response.json()
        except ValueError as exc:
            raise ProviderFetchError(
                "Invalid JSON from GoodWe login",
                details={"body": response.text},
            ) from exc

        if payload.get("code") != 0:
            raise ProviderError(payload.get("msg", "GoodWe login failed"))

        data = payload["data"]

        # 🔥 SEMS returns correct API host
        api_base = payload.get("api")
        if not api_base:
            raise ProviderError("Missing API base URL from GoodWe")

        self.base_url = api_base.rstrip("/")

        self._token_ctx = {
            "uid": data["uid"],
            "timestamp": data["timestamp"],
            "token": data["token"],
            "client": "web",
            "language": data.get("language", "zh_CN"),
            "ver": self.SEMS_VER,
        }

        self._logged_in = True
        logger.info("[GOODWE LOGIN OK] uid=%s", data["uid"])

    def _token_header(self) -> str:
        if not self._token_ctx:
            raise ProviderError("GoodWe adapter not authenticated")
        return json.dumps(self._token_ctx, separators=(",", ":"))

    def _post(self, path: str, payload: Mapping[str, Any]) -> Any:
        self._authenticate()

        body = dict(payload)
        body["ver"] = self.SEMS_VER

        response = self._request(
            "POST",
            path,
            json_data=body,
            headers={
                "Content-Type": "application/json;charset=UTF-8",
                "Accept": "application/json, text/plain, */*",
                "User-Agent": "Mozilla/5.0",
                "Token": self._token_header(),
            },
        )

        try:
            data = response.json()
        except ValueError as exc:
            raise ProviderFetchError(
                "Invalid JSON from GoodWe API",
                details={"body": response.text},
            ) from exc

        if data.get("code") not in (0, "0", None):
            raise ProviderError(
                message=data.get("msg", "GoodWe API error"),
                details={
                    "code": data.get("code"),
                    "response": data,
                    "path": path,
                },
            )

        return data.get("data")
