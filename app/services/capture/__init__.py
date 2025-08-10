from __future__ import annotations

from typing import Optional

from PIL import Image

from app.config import settings


def capture_frame(serial: Optional[str] = None) -> Image.Image:
    """
    Capture a single RGB frame from the active emulator/game window.

    Backends:
    - "adb": use ADB screencap from a connected device/emulator
    - "window": capture a Windows window client-area by title hint (Google Play Games Beta)
    - "auto" (default): try ADB first; if none connected, try window capture
    """
    backend = (settings.capture_backend or "auto").lower()

    if backend == "adb":
        return _capture_via_adb(serial)
    if backend == "window":
        return _capture_via_window()

    # auto
    try:
        return _capture_via_adb(serial)
    except Exception:
        return _capture_via_window()


def _capture_via_adb(serial: Optional[str]) -> Image.Image:
    # Import locally to avoid platform-specific imports at module import time
    from app.services.capture.adb_capture import capture_frame as adb_capture_frame

    return adb_capture_frame(serial)


def _capture_via_window() -> Image.Image:
    # Import locally to avoid Windows-only imports at module import time
    from app.services.capture.window_capture import capture_window
    from app.services.capture.window_manage import (
        find_window_handle,
        get_foreground_window,
        set_foreground_window,
    )

    title_hint = settings.window_title_hint
    # Best effort: bring target window to foreground if configured, without spawning external processes
    try:
        if settings.window_force_foreground and title_hint:
            hwnd = find_window_handle(title_hint)
            if hwnd and hwnd != get_foreground_window():
                set_foreground_window(hwnd)
    except Exception:
        pass
    return capture_window(title_hint)


