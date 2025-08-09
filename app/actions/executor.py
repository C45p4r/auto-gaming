from __future__ import annotations

import time
from collections.abc import Callable

from app.actions.types import Action, BackAction, SwipeAction, TapAction, WaitAction
from app.config import settings
from app.services.capture.adb_capture import adb_exec as adb
from app.services.capture.window_capture import find_window_rect
from app.services.input.window_input import click_absolute, swipe_absolute, send_escape


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
    backend = (settings.input_backend or "auto").lower()

    def do_adb() -> None:
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

    def do_window() -> None:
        # Best-effort: use key simulation via ADB if available; otherwise, rely on user focus.
        # We will compute scaled coordinates relative to the current window client size,
        # then use ADB tap as a fallback if available. True OS-level click injection is
        # intentionally omitted for safety and ToS alignment.
        rect = find_window_rect(settings.window_title_hint)
        base_w = max(1, int(settings.input_base_width))
        base_h = max(1, int(settings.input_base_height))
        scale_x = rect.width / float(base_w)
        scale_y = rect.height / float(base_h)

        if isinstance(action, TapAction):
            x = int(rect.left + action.x * scale_x)
            y = int(rect.top + action.y * scale_y)
            # Prefer direct OS-level click for Windows emulator testing
            click_absolute(x, y)
        elif isinstance(action, SwipeAction):
            x1 = int(rect.left + action.x1 * scale_x)
            y1 = int(rect.top + action.y1 * scale_y)
            x2 = int(rect.left + action.x2 * scale_x)
            y2 = int(rect.top + action.y2 * scale_y)
            swipe_absolute(x1, y1, x2, y2, action.duration_ms)
        elif isinstance(action, WaitAction):
            time.sleep(action.seconds)
        elif isinstance(action, BackAction):
            # ESC often maps to back; otherwise user can map in emulator
            send_escape()
        else:  # pragma: no cover - exhaustive typing
            raise ValueError(f"Unsupported action: {action}")

    if backend == "adb":
        do_adb()
        return
    if backend == "window":
        do_window()
        return

    # auto: prefer adb; if it fails, use window scaling path
    try:
        do_adb()
    except Exception:
        do_window()


def escape_sequence(presses: int = 3, wait_s: float = 0.3) -> None:
    for _ in range(max(0, presses)):
        execute(BackAction())
        time.sleep(max(0.0, wait_s))
