def _parse_watt(value: str | None) -> float:
    if not value:
        return 0.0
    return round(float(value.replace("W", "").strip()), 2)
