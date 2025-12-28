from __future__ import annotations


class WizardError(Exception):
    """Base exception for wizard workflow failures."""


class WizardNotConfiguredError(WizardError):
    """Raised when the requested provider has no wizard definition."""


class WizardStepNotFoundError(WizardError):
    """Raised when a wizard step cannot be resolved."""


class WizardSessionExpiredError(WizardError):
    """Raised when a previously created wizard session is no longer valid."""


class WizardSessionStateError(WizardError):
    """Raised when a handler discovers inconsistent session data."""


class WizardResultError(WizardError):
    """Raised when a wizard step produces inconsistent result data."""
