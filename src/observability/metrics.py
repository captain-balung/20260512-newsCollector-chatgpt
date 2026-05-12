"""In-process metric counter (SRS §11.1). Persisted into run_metrics on finish."""
from __future__ import annotations

from collections import defaultdict
from time import perf_counter


class Metrics:
    """Tiny metrics collector — counters, gauges, timers."""

    def __init__(self) -> None:
        self.started_at = perf_counter()
        self.counters: dict[str, int] = defaultdict(int)
        self.gauges: dict[str, float] = {}
        self.timers: dict[str, float] = {}

    def inc(self, name: str, by: int = 1) -> None:
        self.counters[name] += by

    def gauge(self, name: str, value: float) -> None:
        self.gauges[name] = value

    def timer_start(self, name: str) -> None:
        self.timers[f"_{name}_started_at"] = perf_counter()

    def timer_stop(self, name: str) -> None:
        start = self.timers.pop(f"_{name}_started_at", None)
        if start is None:
            return
        self.timers[name] = round(perf_counter() - start, 3)

    def snapshot(self) -> dict:
        return {
            "elapsed_seconds": round(perf_counter() - self.started_at, 3),
            "counters": dict(self.counters),
            "gauges": dict(self.gauges),
            "timers": {k: v for k, v in self.timers.items() if not k.startswith("_")},
        }
