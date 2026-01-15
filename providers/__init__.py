from .base import BaseProviderAdapter
from .exceptions import (
    ProviderConfigError,
    ProviderFetchError,
    ProviderNotSupportedError,
)
from .adapters.factory import (
    VendorAdapterFactory,
    get_vendor_adapter_factory,
    create_adapter_for_provider,
)

__all__ = [
    "BaseProviderAdapter",
    "ProviderConfigError",
    "ProviderFetchError",
    "ProviderNotSupportedError",
    "VendorAdapterFactory",
    "get_vendor_adapter_factory",
    "create_adapter_for_provider",
]

ProviderAdapterFactory = VendorAdapterFactory


def register_adapter(*args, **kwargs):
    """legacy – adapter registration now happens through provider definitions."""
    raise NotImplementedError(
        "register_adapter is deprecated; use provider definitions"
    )
