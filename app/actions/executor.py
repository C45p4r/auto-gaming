from __future__ import annotations

import time
from collections.abc import Callable

from app.actions.types import Action, BackAction, SwipeAction, TapAction, WaitAction
from app.services.capture.adb_capture import adb_exec as adb


def retry(fn: Callable[[], object], retries: int = 3, backoff_s: float = 0.2) -> None:
    last_exc: Exception | None = None
    for i in range(retries):
        try:
            fn()
            return
        except Exception as exc:  # pragma: no cover - trivial retry
            last_exc = exc
            time.sleep(backoff_s * (2**i))
    if last_exc:
        raise last_exc


def execute(action: Action) -> None:
    if isinstance(action, TapAction):
        retry(lambda: adb(["shell", "input", "tap", str(action.x), str(action.y)]))
    elif isinstance(action, SwipeAction):
        retry(
            lambda: adb(
                [
                    "shell",
                    "input",
                    "swipe",
                    str(action.x1),
                    str(action.y1),
                    str(action.x2),
                    str(action.y2),
                    str(action.duration_ms),
                ]
            )
        )
    elif isinstance(action, WaitAction):
        time.sleep(action.seconds)
    elif isinstance(action, BackAction):
        retry(lambda: adb(["shell", "input", "keyevent", "KEYCODE_BACK"]))
    else:  # pragma: no cover - exhaustive typing
        raise ValueError(f"Unsupported action: {action}")


def escape_sequence(presses: int = 3, wait_s: float = 0.3) -> None:
    for _ in range(max(0, presses)):
        execute(BackAction())
        time.sleep(max(0.0, wait_s))
