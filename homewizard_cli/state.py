"""Delta tracking for polling data."""

import statistics
from collections import deque


class Aggregator:
    """Rolling window aggregator for numeric field statistics."""

    def __init__(self, window_size: int = 20):
        self._window_size = window_size
        self._samples: dict[str, deque[float]] = {}

    def update(self, data: dict) -> dict[str, float]:
        result: dict[str, float] = {}
        for k, v in data.items():
            if isinstance(v, (int, float)):
                samples = self._samples.setdefault(k, deque(maxlen=self._window_size))
                samples.append(float(v))
                if len(samples) >= 2:
                    result[f"{k}_mean"] = statistics.mean(samples)
                    result[f"{k}_min"] = min(samples)
                    result[f"{k}_max"] = max(samples)
                    result[f"{k}_stddev"] = statistics.stdev(samples)
        return result

    def field_count(self, field: str) -> int:
        return len(self._samples.get(field, []))


class DeltaTracker:
    def __init__(self, fields: list[str] | None = None):
        self.fields = fields
        self._previous: dict[str, float] = {}

    def update(self, data: dict) -> dict[str, tuple]:
        changes = {}
        for k, v in data.items():
            if isinstance(v, (int, float)) and (
                self.fields is None or k in self.fields
            ):
                prev = self._previous.get(k)
                if prev is not None and v != prev:
                    changes[k] = (prev, v, v - prev)
                self._previous[k] = v if isinstance(v, float) else float(v)
        return changes

    def changed(self, data: dict) -> bool:
        for k, v in data.items():
            if isinstance(v, (int, float)) and (
                self.fields is None or k in self.fields
            ):
                prev = self._previous.get(k)
                if prev is not None and v != prev:
                    return True
        return False
