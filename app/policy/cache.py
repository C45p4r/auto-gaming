from __future__ import annotations

import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any, Tuple


@dataclass
class CacheEntry:
    score: float
    action: Any
    who: str
    ts: float


class DecisionCache:
    def __init__(self, capacity: int = 256, ttl_s: float = 120.0) -> None:
        self.capacity = int(capacity)
        self.ttl_s = float(ttl_s)
        self._store: OrderedDict[str, CacheEntry] = OrderedDict()

    def get(self, key: str) -> Tuple[float, Any, str] | None:
        now = time.monotonic()
        entry = self._store.get(key)
        if not entry:
            return None
        if now - entry.ts > self.ttl_s:
            # expired
            try:
                del self._store[key]
            except Exception:
                pass
            return None
        # refresh LRU
        self._store.move_to_end(key)
        return entry.score, entry.action, entry.who

    def set(self, key: str, score: float, action: Any, who: str) -> None:
        now = time.monotonic()
        self._store[key] = CacheEntry(score=score, action=action, who=who, ts=now)
        self._store.move_to_end(key)
        # enforce capacity
        while len(self._store) > self.capacity:
            try:
                self._store.popitem(last=False)
            except Exception:
                break


