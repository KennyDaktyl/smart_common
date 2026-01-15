from __future__ import annotations

import logging
from typing import Any, Mapping

from smart_common.providers.definitions.base import ProviderDefinition
from smart_common.providers.definitions.registry import ProviderDefinitionRegistry
from smart_common.providers.enums import ProviderVendor
from smart_common.providers.wizard.base import WizardStepResult
from smart_common.providers.wizard.exceptions import (
    WizardNotConfiguredError,
    WizardResultError,
    WizardSessionExpiredError,
    WizardStepNotFoundError,
)
from smart_common.providers.wizard.factory import ProviderWizardFactory
from smart_common.providers.wizard.session.base import BaseWizardSessionStore
from smart_common.providers.wizard.session.provider import get_wizard_session_store

logger = logging.getLogger(__name__)


class WizardService:
    def __init__(
        self,
        definitions: Mapping[ProviderVendor, ProviderDefinition] | None = None,
        session_store: BaseWizardSessionStore | None = None,
    ) -> None:
        self._definitions = definitions or ProviderDefinitionRegistry.all()
        self._wizard_factory = ProviderWizardFactory(self._definitions)
        self._session_store = session_store or get_wizard_session_store()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_initial_step(self, vendor: ProviderVendor) -> tuple[str, type[Any]]:
        logger.info("Wizard get_initial_step", extra={"vendor": vendor.value})

        wizard = self._wizard_factory.create(vendor)
        step_name = wizard.initial_step
        step = wizard.get_step(step_name)
        if not step:
            raise WizardStepNotFoundError(f"Initial step '{step_name}' missing")

        schema_cls = step.schema
        if schema_cls is None:
            raise WizardStepNotFoundError(
                f"Initial step '{step_name}' must expose a schema"
            )

        return step_name, schema_cls

    def run_step(
        self,
        vendor: ProviderVendor,
        step_name: str,
        payload: Mapping[str, Any] | None = None,
        context: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        logger.info(
            "Wizard run_step",
            extra={
                "vendor": vendor.value,
                "step": step_name,
                "payload": payload,
                "context": context,
            },
        )

        definition = self._definitions.get(vendor)
        if not definition or not definition.wizard_cls:
            raise WizardNotConfiguredError(f"No wizard for provider {vendor.value}")

        wizard = self._wizard_factory.create(vendor)
        step = wizard.get_step(step_name)
        if not step:
            raise WizardStepNotFoundError(
                f"Step '{step_name}' is not available for provider {vendor.value}"
            )

        session = self._resolve_session(
            vendor=vendor,
            context=context or {},
            step_name=step_name,
            wizard=wizard,
        )

        logger.info(
            "Wizard session resolved",
            extra={
                "session_id": session.id,
                "vendor": session.vendor.value,
                "session_data": session.session_data,
                "context": session.context,
            },
        )

        schema_cls = step.schema
        if schema_cls is None:
            model = None
            payload_values = {}
        else:
            model = schema_cls.model_validate(payload or {})
            payload_values = model.model_dump()

        logger.info(
            "Wizard step payload validated",
            extra={
                "step": step_name,
                "payload_values": payload_values,
            },
        )

        result = step.process(model, session.session_data)

        logger.info(
            "Wizard step result",
            extra={
                "step": step_name,
                "result": (
                    result.model_dump()
                    if hasattr(result, "model_dump")
                    else str(result)
                ),
            },
        )

        self._merge_step_result(session, result, step_name, payload_values)

        if self._is_complete(result):
            if result.next_step:
                raise WizardResultError(
                    "Wizard cannot report completion while next_step is set"
                )

            final_config = self._validate_final_config(definition, result.final_config)

            logger.info(
                "Wizard completed",
                extra={
                    "vendor": vendor.value,
                    "session_id": session.id,
                    "final_config": final_config,
                },
            )

            return {
                "vendor": vendor,
                "step": None,
                "schema": None,
                "options": {},
                "context": dict(session.context),
                "is_complete": True,
                "final_config": final_config,
            }

        next_step = result.next_step
        if not next_step:
            raise WizardResultError(
                "Wizard step must define next_step or mark completion"
            )

        next_definition = wizard.get_step(next_step)
        if not next_definition:
            raise WizardStepNotFoundError(
                f"Next step '{next_step}' not found for provider {vendor.value}"
            )

        logger.info(
            "Wizard step completed",
            extra={
                "vendor": vendor.value,
                "step": step_name,
                "next": next_step,
                "session_id": session.id,
            },
        )

        next_schema = next_definition.schema

        return {
            "vendor": vendor,
            "step": next_step,
            "schema": (
                next_schema.model_json_schema() if next_schema is not None else None
            ),
            "options": dict(result.options),
            "context": dict(session.context),
            "is_complete": False,
            "final_config": None,
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _resolve_session(
        self,
        vendor: ProviderVendor,
        context: Mapping[str, Any],
        *,
        step_name: str,
        wizard: Any,
    ):
        session_id = context.get("wizard_session_id")

        if not session_id:
            if step_name == wizard.initial_step:
                session = self._session_store.create(vendor)
                logger.info(
                    "Wizard session created",
                    extra={"session_id": session.id, "vendor": vendor.value},
                )
                return session
            raise WizardSessionExpiredError(
                "wizard_session_id is required for this step"
            )

        session = self._session_store.get(str(session_id))
        if not session:
            raise WizardSessionExpiredError("Wizard session has expired")
        if session.vendor != vendor:
            raise WizardNotConfiguredError("Wizard session vendor mismatch")

        return session

    def _merge_step_result(
        self,
        session,
        result: WizardStepResult,
        step_name: str,
        payload_values: dict[str, Any],
    ) -> None:
        logger.info(
            "Wizard merge_step_result (before)",
            extra={
                "session_id": session.id,
                "step": step_name,
                "session_data": session.session_data,
            },
        )

        if step_name != "auth":
            config = session.session_data.setdefault("config", {})
            config.update(payload_values)

        if result.final_config:
            session.session_data["config"] = dict(result.final_config)
            logger.info(
                "Wizard final_config committed",
                extra={
                    "session_id": session.id,
                    "final_config": result.final_config,
                },
            )

        session.session_data.update(result.session_updates or {})
        session.context = {
            **session.context,
            **(result.context_updates or {}),
        }
        session.context["wizard_session_id"] = session.id
        session.last_step = step_name

        self._session_store.persist(session)

        logger.info(
            "Wizard merge_step_result (after)",
            extra={
                "session_id": session.id,
                "session_data": session.session_data,
                "context": session.context,
            },
        )

    def _is_complete(self, result: WizardStepResult) -> bool:
        return bool(result.is_complete) or bool(result.final_config)

    def _validate_final_config(
        self,
        definition: ProviderDefinition,
        final_config: Mapping[str, Any] | None,
    ) -> dict[str, Any] | None:
        if not final_config:
            return None

        config_schema = definition.config_schema
        if config_schema:
            validated = config_schema.model_validate(final_config).model_dump()
            logger.info(
                "Wizard final_config validated",
                extra={"validated_config": validated},
            )
            return validated

        return dict(final_config)

    def consume_session(
        self,
        wizard_session_id: str,
        *,
        vendor: ProviderVendor | None = None,
    ) -> tuple[ProviderVendor, dict[str, Any], dict[str, Any] | None, dict[str, Any]]:
        session = self._session_store.get(wizard_session_id)
        if not session:
            raise WizardSessionExpiredError("Wizard session has expired")

        if vendor and session.vendor != vendor:
            raise WizardNotConfiguredError("Wizard session vendor mismatch")

        config = dict(session.session_data.get("config", {}))
        credentials = session.session_data.get("credentials")
        context = dict(session.context)

        logger.info(
            "Wizard session consumed",
            extra={
                "session_id": session.id,
                "vendor": session.vendor.value,
                "config": config,
                "credentials_present": bool(credentials),
                "context": context,
            },
        )

        self._session_store.delete(session.id)

        return session.vendor, config, credentials, context
