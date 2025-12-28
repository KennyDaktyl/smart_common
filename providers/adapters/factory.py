from __future__ import annotations

import logging
from inspect import Parameter, signature
from typing import Any, Mapping, Tuple

from smart_common.providers.adapters.base import BaseProviderAdapter
from smart_common.providers.definitions.base import ProviderDefinition, ProviderDefinitionRegistry
from smart_common.providers.enums import ProviderVendor
from smart_common.providers.exceptions import ProviderNotSupportedError

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
