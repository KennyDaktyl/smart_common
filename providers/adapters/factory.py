from __future__ import annotations

import logging
from inspect import Parameter, signature
from typing import Any, Mapping, Tuple

from cryptography.fernet import InvalidToken

from smart_common.core.security import decrypt_secret
from smart_common.models.provider import Provider
from smart_common.providers.adapters.base import BaseProviderAdapter
from smart_common.providers.definitions import registry as _  # ensure definitions register
from smart_common.providers.definitions.base import ProviderDefinition, ProviderDefinitionRegistry
from smart_common.providers.enums import ProviderVendor
from smart_common.providers.exceptions import ProviderConfigError, ProviderNotSupportedError

logger = logging.getLogger(__name__)

_ADAPTER_CACHE: dict[Tuple[ProviderVendor, str], BaseProviderAdapter] = {}


class VendorAdapterFactory:
    """Creates provider adapters and keeps them cached per session key."""

    def __init__(self, definitions: Mapping[ProviderVendor, ProviderDefinition]):
        self._definitions = definitions

    def create(
        self,
        vendor: ProviderVendor,
        *,
        credentials: Mapping[str, Any],
        cache_key: str,
        overrides: Mapping[str, Any] | None = None,
    ) -> BaseProviderAdapter:
        cache_id = (vendor, cache_key)
        cached = _ADAPTER_CACHE.get(cache_id)
        if cached:
            logger.debug(
                "Using cached provider adapter",
                extra={
                    "vendor": vendor.value,
                    "cache_key": cache_key,
                    "adapter": type(cached).__name__,
                },
            )
            return cached

        definition = self._definitions.get(vendor)
        if not definition or not definition.adapter_cls:
            raise ProviderNotSupportedError(vendor.value)

        if not issubclass(definition.adapter_cls, BaseProviderAdapter):
            raise TypeError(
                f"Adapter {definition.adapter_cls.__name__} must extend BaseProviderAdapter"
            )

        adapter_settings = dict(definition.adapter_settings or {})
        if overrides:
            adapter_settings.update(overrides)

        allowed_params = self._filter_adapter_params(definition.adapter_cls, adapter_settings)
        try:
            adapter = definition.adapter_cls(**credentials, **allowed_params)
        except TypeError:
            logger.exception(
                "Failed to instantiate provider adapter",
                extra={
                    "vendor": vendor.value,
                    "adapter": definition.adapter_cls.__name__,
                    "credentials": list(credentials.keys()),
                    "settings": list(allowed_params.keys()),
                },
            )
            raise

        _ADAPTER_CACHE[cache_id] = adapter
        logger.info(
            "Created provider adapter instance",
            extra={
                "vendor": vendor.value,
                "adapter": type(adapter).__name__,
                "cache_key": cache_key,
            },
        )

        return adapter

    def clear_cache(self) -> None:
        _ADAPTER_CACHE.clear()
        logger.warning("Provider adapter cache cleared")

    @staticmethod
    def _filter_adapter_params(
        adapter_cls: type[BaseProviderAdapter], settings: Mapping[str, Any]
    ) -> dict[str, Any]:
        init_sig = signature(adapter_cls.__init__)
        allowed_params = {
            name
            for name, param in init_sig.parameters.items()
            if name != "self"
            and param.kind
            in (
                Parameter.POSITIONAL_ONLY,
                Parameter.POSITIONAL_OR_KEYWORD,
                Parameter.KEYWORD_ONLY,
            )
        }

        has_var_keyword = any(
            param.kind == Parameter.VAR_KEYWORD
            for param in init_sig.parameters.values()
        )

        if has_var_keyword:
            return dict(settings)

        return {k: v for k, v in settings.items() if k in allowed_params}


def get_vendor_adapter_factory() -> VendorAdapterFactory:
    definitions = ProviderDefinitionRegistry.all()
    return VendorAdapterFactory(definitions)


def create_adapter_for_provider(
    provider: Provider,
    *,
    factory: VendorAdapterFactory | None = None,
) -> BaseProviderAdapter:
    vendor = provider.vendor
    if vendor is None:
        raise ProviderConfigError(
            "Provider vendor missing",
            details={"provider_id": provider.id},
        )

    connect_credentials = _resolve_provider_credentials(provider)
    if not connect_credentials:
        raise ProviderConfigError(
            "Provider credentials are missing",
            details={"provider_id": provider.id, "vendor": vendor.value},
        )

    external_id = provider.external_id
    if not external_id:
        raise ProviderConfigError(
            "Provider external_id is required for polling",
            details={"provider_id": provider.id, "vendor": vendor.value},
        )

    factory = factory or get_vendor_adapter_factory()

    cache_key = f"{vendor.value}:{external_id}"
    adapter = factory.create(
        vendor,
        credentials=connect_credentials,
        cache_key=cache_key,
    )

    # keep runtime metadata on the adapter to avoid re-fetching
    setattr(adapter, "provider_external_id", external_id)
    setattr(adapter, "provider_id", provider.id)

    if getattr(provider, "external_id", None):
        setattr(adapter, "_external_id", provider.external_id)

    return adapter


def _resolve_provider_credentials(provider: Provider) -> dict[str, str]:
    credentials = getattr(provider, "credentials", None)
    if credentials is None:
        return {}

    payload: dict[str, str] = {}

    attr_mapping = {
        "login": ("username",),
        "password": ("password",),
        "token": ("token",),
        "refresh_token": ("refresh_token",),
    }

    for attr, target_keys in attr_mapping.items():
        raw_value = getattr(credentials, attr, None)
        if raw_value is None:
            continue

        try:
            decrypted = _decrypt_secret(raw_value)
        except InvalidToken as exc:
            raise ProviderConfigError(
                "Failed to decrypt provider credential",
                details={
                    "provider_id": provider.id,
                    "vendor": provider.vendor.value if provider.vendor else None,
                    "attribute": attr,
                },
            ) from exc

        for key in target_keys:
            payload[key] = decrypted

    return payload


def _decrypt_secret(value: str) -> str:
    return decrypt_secret(value)
