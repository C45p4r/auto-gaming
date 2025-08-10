from __future__ import annotations

import time

from app.reliability.flake import FlakeTracker, FlakeConfig


def test_quarantine_triggers_and_expires() -> None:
    cfg = FlakeConfig(window_s=2.0, threshold=2, quarantine_s=1.0)
    ft = FlakeTracker(cfg)
    assert ft.in_quarantine is False
    ft.record_error("e1")
    assert ft.in_quarantine is False
    ft.record_error("e2")
    assert ft.in_quarantine is True
    time.sleep(1.1)
    assert ft.in_quarantine is False


