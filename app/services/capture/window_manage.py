from __future__ import annotations

import ctypes
import ctypes.wintypes as wintypes
import re
from dataclasses import dataclass
from typing import Optional


user32 = ctypes.windll.user32  # type: ignore[attr-defined]


EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)

GWL_STYLE = -16
GWL_EXSTYLE = -20

HWND_TOPMOST = -1
HWND_NOTOPMOST = -2

SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_NOACTIVATE = 0x0010
SWP_SHOWWINDOW = 0x0040
SWP_NOZORDER = 0x0004

SW_RESTORE = 9


def get_foreground_window() -> int:
    return int(user32.GetForegroundWindow())


def set_foreground_window(hwnd: int) -> None:
    user32.SetForegroundWindow(hwnd)


class WindowManageError(RuntimeError):
    pass


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


def _get_window_text(hwnd: int) -> str:
    length = user32.GetWindowTextLengthW(hwnd)
    buffer = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buffer, length + 1)
    return buffer.value


def _is_window_visible(hwnd: int) -> bool:
    return bool(user32.IsWindowVisible(hwnd))


def _match_title(title: str, title_hint: Optional[str]) -> bool:
    if not title or not title_hint:
        return False
    try:
        pattern = re.compile(title_hint, re.IGNORECASE)
        return bool(pattern.search(title))
    except re.error:
        return title_hint.lower() in title.lower()


def find_window_handle(title_hint: Optional[str]) -> int:
    hwnd_result: Optional[int] = None

    def callback(hwnd: int, _lparam: int) -> bool:
        nonlocal hwnd_result
        if not _is_window_visible(hwnd):
            return True
        title = _get_window_text(hwnd)
        if not title:
            return True
        if _match_title(title, title_hint):
            hwnd_result = hwnd
            return False
        return True

    user32.EnumWindows(EnumWindowsProc(callback), 0)
    if hwnd_result is None:
        raise WindowManageError(f"No visible window matched title hint: {title_hint!r}")
    return hwnd_result


def get_client_rect(hwnd: int) -> WindowRect:
    rect = wintypes.RECT()
    if not user32.GetClientRect(hwnd, ctypes.byref(rect)):
        raise WindowManageError("GetClientRect failed")
    pt = wintypes.POINT(0, 0)
    if not user32.ClientToScreen(hwnd, ctypes.byref(pt)):
        raise WindowManageError("ClientToScreen failed")
    left = pt.x
    top = pt.y
    right = left + rect.right - rect.left
    bottom = top + rect.bottom - rect.top
    return WindowRect(left=left, top=top, right=right, bottom=bottom)


def set_topmost(hwnd: int, topmost: bool = True) -> None:
    insert_after = HWND_TOPMOST if topmost else HWND_NOTOPMOST
    user32.SetWindowPos(hwnd, insert_after, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW)


def _get_styles(hwnd: int) -> tuple[int, int]:
    get_long = user32.GetWindowLongW
    style = get_long(hwnd, GWL_STYLE)
    exstyle = get_long(hwnd, GWL_EXSTYLE)
    return style, exstyle


def move_resize(hwnd: int, left: int, top: int, width: int, height: int, client_area: bool = True) -> None:
    # Restore if minimized
    user32.ShowWindow(hwnd, SW_RESTORE)

    w = width
    h = height
    if client_area:
        style, exstyle = _get_styles(hwnd)
        rect = wintypes.RECT(0, 0, width, height)
        if not user32.AdjustWindowRectEx(ctypes.byref(rect), style, False, exstyle):
            raise WindowManageError("AdjustWindowRectEx failed")
        w = rect.right - rect.left
        h = rect.bottom - rect.top

    user32.SetWindowPos(
        hwnd,
        0,
        int(left),
        int(top),
        int(w),
        int(h),
        SWP_NOZORDER | SWP_SHOWWINDOW,
    )

