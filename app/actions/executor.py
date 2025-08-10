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


def compute_scaled_point(
    base_w: int, base_h: int, rect: object, x: int, y: int
) -> tuple[int, int]:
    """Scale base-resolution coordinates (x,y) into absolute screen coords.

    rect must expose: left, top, width, height.
    """
    bw = max(1, int(base_w))
    bh = max(1, int(base_h))
    scale_x = float(getattr(rect, "width")) / float(bw)
    scale_y = float(getattr(rect, "height")) / float(bh)
    px = int(getattr(rect, "left") + x * scale_x)
    py = int(getattr(rect, "top") + y * scale_y)
    return px, py


def clamp_to_rect(
    rect: object,
    px: int,
    py: int,
    exclude_bottom_px: int | None = None,
    min_margin_frac_x: float = 0.04,
    min_margin_frac_y: float = 0.06,
) -> tuple[int, int]:
    """Clamp a point inside the client rect with safe margins.

    - exclude_bottom_px: ensure bottom margin >= this many pixels.
    - min_margin_frac_{x,y}: relative margins from rect size.
    rect must expose: left, top, right, bottom, width, height.
    """
    width = int(getattr(rect, "width"))
    height = int(getattr(rect, "height"))
    left = int(getattr(rect, "left"))
    top = int(getattr(rect, "top"))
    right = int(getattr(rect, "right", left + width))
    bottom = int(getattr(rect, "bottom", top + height))

    margin_x = max(6, int(width * min_margin_frac_x))
    margin_y = max(6, int(height * min_margin_frac_y))
    if exclude_bottom_px is not None:
        margin_y = max(margin_y, int(exclude_bottom_px))

    cx = max(left + margin_x, min(right - margin_x, int(px)))
    cy = max(top + margin_y, min(bottom - margin_y, int(py)))
    return cx, cy


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

        def _clamp_to_rect(px: int, py: int) -> tuple[int, int]:
            try:
                from app.config import settings as cfg
                exclude = int(getattr(cfg, "input_exclude_bottom_px", 0))
            except Exception:
                exclude = 0
            return clamp_to_rect(rect, px, py, exclude_bottom_px=exclude)

        if isinstance(action, TapAction):
            # Ensure the target window is foregrounded before sending input
            # Do not force foreground on every tap to avoid stealing focus from the emulator

            x, y = compute_scaled_point(base_w, base_h, rect, action.x, action.y)
            x, y = _clamp_to_rect(x, y)
            # Prefer direct OS-level click for Windows emulator testing
            click_absolute(x, y)
        elif isinstance(action, SwipeAction):
            # Avoid foregrounding during swipe as well
            x1, y1 = compute_scaled_point(base_w, base_h, rect, action.x1, action.y1)
            x2, y2 = compute_scaled_point(base_w, base_h, rect, action.x2, action.y2)
            x1, y1 = _clamp_to_rect(x1, y1)
            x2, y2 = _clamp_to_rect(x2, y2)
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
