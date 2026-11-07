"""Telemetry metrics, token estimators, and statistical aggregation."""
import statistics
from typing import Any, Dict, List, Optional


def estimate_token_count(text: str) -> int:
    """Accurate offline token count estimator (heuristic: ~4 chars per token)."""
    if not text:
        return 0
    words = text.strip().split()
    return max(1, int(len(words) * 1.3) + len(text) // 25)


def calculate_percentiles(values: List[float]) -> Dict[str, float]:
    """Calculate p50 (median), p90, and p95 percentiles from a series."""
    if not values:
        return {"p50": 0.0, "p90": 0.0, "p95": 0.0, "mean": 0.0}

    sorted_vals = sorted(values)
    n = len(sorted_vals)

    def get_percentile(p: float) -> float:
        idx = max(0, min(n - 1, int(math.ceil(p * n)) - 1))
        return sorted_vals[idx]

    import math

    return {
        "p50": round(statistics.median(sorted_vals), 2),
        "p90": round(get_percentile(0.90), 2),
        "p95": round(get_percentile(0.95), 2),
        "mean": round(statistics.mean(sorted_vals), 2),
    }

