from .base import BaseProviderAdapter
from .exceptions import (
    ProviderConfigError,
    ProviderFetchError,
    ProviderNotSupportedError,
)
from .adapters.factory import (
    VendorAdapterFactory,
    get_vendor_adapter_factory,
)
from .models import NormalizedMeasurement

ProviderAdapterFactory = VendorAdapterFactory


def register_adapter(*args, **kwargs):
    """legacy – adapter registration now happens through provider definitions."""
    raise NotImplementedError(
        "register_adapter is deprecated; use provider definitions"
    )
