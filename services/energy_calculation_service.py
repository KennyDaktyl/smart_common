# smart_common/services/energy_calculation_service.py

from dataclasses import dataclass
from datetime import datetime
from collections import defaultdict


@dataclass(frozen=True)
class PowerSample:
    ts: datetime
    value: float


class EnergyCalculationService:
    @staticmethod
    def integrate_hourly(samples: list[PowerSample]) -> dict[datetime, float]:
        """
        Zwraca energię w JEDNOSTCE PROVIDERA:
        - jeśli power był w kW → wynik w kWh
        - jeśli power był w W  → wynik w Wh
        """
        energy_by_hour: dict[datetime, float] = defaultdict(float)

        if len(samples) < 2:
            return energy_by_hour

        for i in range(len(samples) - 1):
            a = samples[i]
            b = samples[i + 1]

            dt_hours = (b.ts - a.ts).total_seconds() / 3600
            if dt_hours <= 0:
                continue

            energy = a.value * dt_hours

            hour_bucket = a.ts.replace(
                minute=0, second=0, microsecond=0
            )

            energy_by_hour[hour_bucket] += energy

        return energy_by_hour
