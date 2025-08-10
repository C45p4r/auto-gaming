from __future__ import annotations

import time

from app.policy.cache import DecisionCache


def test_cache_set_get_and_expire() -> None:
    c = DecisionCache(capacity=2, ttl_s=0.3)
    c.set("k1", 0.9, {"type": "wait"}, "policy-lite")
    v = c.get("k1")
    assert v is not None and v[2] == "policy-lite"
    time.sleep(0.35)
    assert c.get("k1") is None


def test_cache_lru_capacity() -> None:
    c = DecisionCache(capacity=2, ttl_s=10.0)
    c.set("a", 0.1, {"type": "tap"}, "p1")
    c.set("b", 0.2, {"type": "tap"}, "p2")
    c.set("c", 0.3, {"type": "tap"}, "p3")
    # oldest (a) should be evicted
    assert c.get("a") is None
    assert c.get("b") is not None
    assert c.get("c") is not None


