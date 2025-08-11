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


def compute_reward(prev: dict[str, float] | None, cur: dict[str, float]) -> float:
    """Compute a scalar reward from metrics delta.

    Positive: daily_progress increase
    Negative: blocks, stuck_events, decision_latency increases
    """
    if prev is None:
        return 0.0
    reward = 0.0
    dp_prev = float(prev.get("daily_progress", 0.0))
    dp_cur = float(cur.get("daily_progress", 0.0))
    reward += (dp_cur - dp_prev) * 1.0
    blocks_prev = float(prev.get("blocks", 0.0))
    blocks_cur = float(cur.get("blocks", 0.0))
    reward -= max(0.0, blocks_cur - blocks_prev) * 1.0
    stuck_prev = float(prev.get("stuck_events", 0.0))
    stuck_cur = float(cur.get("stuck_events", 0.0))
    reward -= max(0.0, stuck_cur - stuck_prev) * 0.5
    lat_prev = float(prev.get("decision_latency_ms", 0.0))
    lat_cur = float(cur.get("decision_latency_ms", 0.0))
    reward -= max(0.0, lat_cur - lat_prev) * 0.001
    return reward


store = MetricsStore()
