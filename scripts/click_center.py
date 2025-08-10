from __future__ import annotations

import time

from app.config import settings
from app.services.capture.window_capture import find_window_rect
from app.services.capture.window_manage import find_window_handle, set_foreground_window
from app.services.input.window_input import click_absolute


def main() -> None:
    rect = find_window_rect(settings.window_title_hint)
    try:
        hwnd = find_window_handle(settings.window_title_hint)
        set_foreground_window(hwnd)
        time.sleep(0.05)
    except Exception:
        pass
    cx = rect.left + rect.width // 2
    cy = rect.top + rect.height // 2
    print(f"Clicking window center at: {cx},{cy}")
    click_absolute(cx, cy)
    print("Click dispatched")


if __name__ == "__main__":
    main()


