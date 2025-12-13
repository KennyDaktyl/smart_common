from __future__ import annotations

from typing import Any, Callable, Dict, Tuple, Type

from smart_common.enums.provider import ProviderType
from smart_common.schemas.provider_schema import ProviderBase

from .base import BaseProviderAdapter
from .exceptions import ProviderConfigError, ProviderNotSupportedError

RegistryKey = Tuple[str, str]
VendorStrategy = Callable[[ProviderBase], str]


class ProviderAdapterFactory:
    _vendor_registry: Dict[RegistryKey, Type[BaseProviderAdapter]] = {}
    _type_registry: Dict[str, Type[BaseProviderAdapter]] = {}

    @classmethod
    def register(
        cls,
        provider_type: ProviderType | str,
        adapter_cls: Type[BaseProviderAdapter],
        *,
        vendor: str | None = None,
    ) -> None:
        type_key = _normalize_provider_type(provider_type)
        if vendor:
            cls._vendor_registry[(type_key, _normalize_vendor(vendor))] = adapter_cls
        else:
            cls._type_registry[type_key] = adapter_cls

    @classmethod
    def create(cls, config: ProviderBase) -> BaseProviderAdapter:
        if not config.provider_type:
            raise ProviderConfigError("provider_type is required")

        type_key = _normalize_provider_type(config.provider_type)
        vendor_key = _normalize_vendor(config.vendor)

        adapter_cls = cls._vendor_registry.get((type_key, vendor_key))
        if not adapter_cls:
            adapter_cls = cls._type_registry.get(type_key)

        if not adapter_cls:
            raise ProviderNotSupportedError(
                f"No adapter registered for type={type_key} vendor={vendor_key}"
            )

        return adapter_cls(config)


def register_adapter(provider_type: ProviderType | str, *, vendor: str | None = None) -> Any:
    def decorator(adapter_cls: Type[BaseProviderAdapter]) -> Type[BaseProviderAdapter]:
        ProviderAdapterFactory.register(provider_type, adapter_cls, vendor=vendor)
        return adapter_cls

    return decorator


def _normalize_provider_type(value: ProviderType | str) -> str:
    if isinstance(value, ProviderType):
        return value.value
    return str(value).lower()


def _normalize_vendor(vendor: str | None) -> str:
    return vendor.strip().lower() if vendor else ""
