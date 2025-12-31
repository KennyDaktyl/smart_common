from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Type

from pydantic import BaseModel

from smart_common.providers.enums import ProviderVendor


@dataclass
class WizardStepResult:
    next_step: str | None = None
    options: dict[str, Any] = field(default_factory=dict)
    context_updates: dict[str, Any] = field(default_factory=dict)
    session_updates: dict[str, Any] = field(default_factory=dict)
    final_config: dict[str, Any] | None = None
    is_complete: bool = False


class WizardStep(ABC):
    name: str
    schema: Type[BaseModel] | None

    @abstractmethod
    def process(
        self,
        payload: BaseModel | None,
        session_data: Mapping[str, Any],
    ) -> WizardStepResult:
        """Execute handler logic for this step."""


class ProviderWizard(ABC):
    vendor: ProviderVendor

    def __init__(self, steps: List[WizardStep]) -> None:
        if not steps:
            raise ValueError("ProviderWizard requires at least one step")
        self._steps: Dict[str, WizardStep] = {step.name: step for step in steps}
        self.steps = steps

    def get_step(self, name: str) -> WizardStep | None:
        return self._steps.get(name)

    @property
    def initial_step(self) -> str:
        return self.steps[0].name

    @property
    def step_names(self) -> List[str]:
        return list(self._steps.keys())
