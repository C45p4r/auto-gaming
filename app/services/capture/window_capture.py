from __future__ import annotations

import ctypes
import ctypes.wintypes as wintypes
import re
from dataclasses import dataclass
from typing import Callable, Optional

from PIL import ImageGrab, Image


class WindowCaptureError(RuntimeError):
    pass


user32 = ctypes.windll.user32  # type: ignore[attr-defined]


EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)


def _get_window_text(hwnd: int) -> str:
    length = user32.GetWindowTextLengthW(hwnd)
    buffer = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buffer, length + 1)
    return buffer.value


def _is_window_visible(hwnd: int) -> bool:
    return bool(user32.IsWindowVisible(hwnd))


@dataclass(frozen=True)
class WindowRect:
    left: int
    top: int
    right: int
    bottom: int

    @property
    def width(self) -> int:
        return max(0, self.right - self.left)

    @property
    def height(self) -> int:
        return max(0, self.bottom - self.top)


def _client_rect_to_screen(hwnd: int) -> WindowRect:
    rect = wintypes.RECT()
    if not user32.GetClientRect(hwnd, ctypes.byref(rect)):
        raise WindowCaptureError("GetClientRect failed")
    # Convert client-area origin to screen coordinates
    pt = wintypes.POINT(0, 0)
    if not user32.ClientToScreen(hwnd, ctypes.byref(pt)):
        raise WindowCaptureError("ClientToScreen failed")
    left = pt.x
    top = pt.y
    right = left + rect.right - rect.left
    bottom = top + rect.bottom - rect.top
    return WindowRect(left=left, top=top, right=right, bottom=bottom)


def _match_title(title: str, title_hint: Optional[str]) -> bool:
    if not title:
        return False
    if not title_hint:
        return False
    try:
        pattern = re.compile(title_hint, re.IGNORECASE)
        return bool(pattern.search(title))
    except re.error:
        # Fallback to simple case-insensitive containment if regex invalid
        return title_hint.lower() in title.lower()


def find_window_rect(title_hint: Optional[str]) -> WindowRect:
    result_rect: Optional[WindowRect] = None

    def callback(hwnd: int, _lparam: int) -> bool:
        nonlocal result_rect
        if not _is_window_visible(hwnd):
            return True
        title = _get_window_text(hwnd)
        if not title:
            return True
        if _match_title(title, title_hint):
            try:
                rect = _client_rect_to_screen(hwnd)
                # Ensure non-zero size
                if rect.width > 0 and rect.height > 0:
                    result_rect = rect
                    return False  # stop enumeration
            except WindowCaptureError:
                pass
        return True

    user32.EnumWindows(EnumWindowsProc(callback), 0)
    if result_rect is None:
        raise WindowCaptureError(
            f"No matching window found for title hint: {title_hint!r}. Ensure Google Play Games Beta is running and visible."
        )
    return result_rect


def capture_window(title_hint: Optional[str]) -> Image.Image:
    rect = find_window_rect(title_hint)
    # bbox is (left, top, right, bottom)
    bbox = (rect.left, rect.top, rect.right, rect.bottom)
    img = ImageGrab.grab(bbox=bbox, all_screens=True)
    return img.convert("RGB")

