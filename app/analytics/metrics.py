from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime


@dataclass(frozen=True)
class MetricPoint:
    ts: str
    value: float


class MetricsStore:
    def __init__(self) -> None:
        self._series: dict[str, list[MetricPoint]] = {}
        self._cap = 1000

    def add_point(self, name: str, value: float) -> None:
        ts = datetime.now(tz=UTC).isoformat()
        arr = self._series.setdefault(name, [])
        arr.append(MetricPoint(ts=ts, value=float(value)))
        if len(arr) > self._cap:
            del arr[0 : len(arr) - self._cap]

    def get_series(self, names: list[str] | None = None) -> dict[str, list[MetricPoint]]:
        if names is None:
            return self._series
        return {n: self._series.get(n, []) for n in names}


store = MetricsStore()
