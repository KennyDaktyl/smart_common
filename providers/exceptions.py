# providers/exceptions.py
from __future__ import annotations


class ProviderConfigError(Exception):
    """Raised when the supplied provider configuration is invalid."""


class ProviderNotSupportedError(Exception):
    """Raised when no adapter exists for a provider type/vendor."""


class ProviderFetchError(Exception):
    """Raised when fetching measurement data fails."""
