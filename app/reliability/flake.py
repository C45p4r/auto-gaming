from __future__ import annotations

import time
from collections import deque, defaultdict
from dataclasses import dataclass
from typing import Deque, Dict

try:
    from app.config import settings
except Exception:  # pragma: no cover - settings import safety
    settings = None  # type: ignore


def _now() -> float:
    return time.monotonic()


@dataclass
class FlakeConfig:
    window_s: float = 30.0
    threshold: int = 3
    quarantine_s: float = 10.0


class FlakeTracker:
    """Tracks recent errors to detect flaky loops and enter a short quarantine.

    When the number of errors within a sliding window exceeds the threshold,
    quarantine is activated for `quarantine_s` seconds. During quarantine the
    caller should avoid risky actions (e.g., only Wait/Back) until it clears.
    """

    def __init__(self, cfg: FlakeConfig | None = None) -> None:
        if cfg is None:
            # read from settings if available
            w = getattr(settings, "flake_window_s", 30.0) if settings else 30.0
            t = getattr(settings, "flake_threshold", 3) if settings else 3
            q = getattr(settings, "quarantine_s", 10.0) if settings else 10.0
            cfg = FlakeConfig(window_s=float(w), threshold=int(t), quarantine_s=float(q))
        self.cfg = cfg
        self._events: Deque[float] = deque()
        self._by_fp: Dict[str, int] = defaultdict(int)
        self._quarantine_until: float = 0.0

    def record_error(self, fingerprint: str | None) -> None:
        now = _now()
        self._events.append(now)
        if fingerprint:
            self._by_fp[fingerprint] += 1
        self._prune(now)
        if len(self._events) >= self.cfg.threshold:
            self._quarantine_until = max(self._quarantine_until, now + self.cfg.quarantine_s)

    def clear(self) -> None:
        self._events.clear()
        self._by_fp.clear()
        self._quarantine_until = 0.0

    def _prune(self, now: float | None = None) -> None:
        if now is None:
            now = _now()
        while self._events and (now - self._events[0]) > self.cfg.window_s:
            self._events.popleft()

    @property
    def in_quarantine(self) -> bool:
        return _now() < self._quarantine_until


