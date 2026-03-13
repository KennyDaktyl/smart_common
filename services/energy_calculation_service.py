# smart_common/services/energy_calculation_service.py

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass(frozen=True)
class PowerSample:
    ts: datetime
    value: float


@dataclass(frozen=True)
class EnergyInterval:
    ts: datetime
    energy: float


class EnergyCalculationService:
    @staticmethod
    def integrate_intervals(
        samples: list[PowerSample],
        *,
        max_interval_seconds: float | None = None,
    ) -> list[EnergyInterval]:
        intervals: list[EnergyInterval] = []
        if len(samples) < 2:
            return intervals

        for i in range(len(samples) - 1):
            a = samples[i]
            b = samples[i + 1]

            interval_end = b.ts
            if max_interval_seconds is not None and max_interval_seconds > 0:
                capped_end = a.ts + timedelta(seconds=max_interval_seconds)
                if capped_end < interval_end:
                    interval_end = capped_end

            dt_hours = (interval_end - a.ts).total_seconds() / 3600
            if dt_hours <= 0:
                continue

            energy = a.value * dt_hours
            intervals.append(EnergyInterval(ts=a.ts, energy=energy))
        return intervals

    @staticmethod
    def integrate_hourly(
        samples: list[PowerSample],
        *,
        max_interval_seconds: float | None = None,
    ) -> dict[datetime, float]:
        """
        Zwraca energię w JEDNOSTCE PROVIDERA:
        - jeśli power był w kW → wynik w kWh
        - jeśli power był w W  → wynik w Wh
        """
        energy_by_hour: dict[datetime, float] = defaultdict(float)

        for left, right in zip(samples, samples[1:]):
            interval_start = left.ts
            interval_end = right.ts
            if max_interval_seconds is not None and max_interval_seconds > 0:
                capped_end = interval_start + timedelta(seconds=max_interval_seconds)
                if capped_end < interval_end:
                    interval_end = capped_end
            if interval_end <= interval_start:
                continue

            total_dt_hours = (interval_end - interval_start).total_seconds() / 3600.0
            if total_dt_hours <= 0:
                continue

            interval_energy = left.value * total_dt_hours
            if interval_energy == 0:
                continue
            cursor = interval_start
            while cursor < interval_end:
                hour_bucket = cursor.replace(minute=0, second=0, microsecond=0)
                next_hour = hour_bucket + timedelta(hours=1)
                segment_end = min(interval_end, next_hour)
                dt_hours = (segment_end - cursor).total_seconds() / 3600.0
                if dt_hours > 0:
                    energy_by_hour[hour_bucket] += interval_energy * (
                        dt_hours / total_dt_hours
                    )
                cursor = segment_end
        return energy_by_hour
