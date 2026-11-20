"""Wilson score intervals for proportions."""

from __future__ import annotations

import math

Z95 = 1.959963984540054


def wilson(k: int, n: int, z: float = Z95) -> tuple[float, float]:
    """95% Wilson score interval for k successes out of n. (0, 0) when n is 0."""
    if n == 0:
        return 0.0, 0.0
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return max(0.0, centre - half), min(1.0, centre + half)


def proportion(k: int, n: int, *, date: str, label: str, unit: str) -> dict:
    lo, hi = wilson(k, n)
    return {
        "label": label,
        "unit": unit,
        "k": k,
        "n": n,
        "pct": round(100 * k / n, 1) if n else None,
        "ci_low": round(100 * lo, 1),
        "ci_high": round(100 * hi, 1),
        "method": "Wilson score 95%",
        "date": date,
    }
