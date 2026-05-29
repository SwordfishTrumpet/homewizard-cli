"""Delta tracking for polling data."""


class DeltaTracker:
    def __init__(self, fields: list[str] | None = None):
        self.fields = fields
        self._previous: dict[str, float] = {}

    def update(self, data: dict) -> dict[str, tuple]:
        changes = {}
        for k, v in data.items():
            if isinstance(v, (int, float)):
                if self.fields is None or k in self.fields:
                    prev = self._previous.get(k)
                    if prev is not None and v != prev:
                        changes[k] = (prev, v, v - prev)
                    self._previous[k] = v if isinstance(v, float) else float(v)
        return changes

    def changed(self, data: dict) -> bool:
        for k, v in data.items():
            if isinstance(v, (int, float)):
                if self.fields is None or k in self.fields:
                    prev = self._previous.get(k)
                    if prev is not None and v != prev:
                        return True
        return False
