from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Sequence


@dataclass(frozen=True)
class NormalizedMeasurement:
    provider_id: int
    value: float | None
    unit: str
    measured_at: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)
    extra_metrics: Sequence[Any] = field(default_factory=tuple)
