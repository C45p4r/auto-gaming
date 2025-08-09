from __future__ import annotations

import ctypes
import time
from typing import Tuple


user32 = ctypes.windll.user32  # type: ignore[attr-defined]


# Constants from WinUser.h
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_ABSOLUTE = 0x8000

INPUT_MOUSE = 0
INPUT_KEYBOARD = 1

KEYEVENTF_KEYUP = 0x0002
VK_ESCAPE = 0x1B


class MOUSEINPUT(ctypes.Structure):
    _fields_ = (
        ("dx", ctypes.c_long),
        ("dy", ctypes.c_long),
        ("mouseData", ctypes.c_ulong),
        ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    )


class KEYBDINPUT(ctypes.Structure):
    _fields_ = (
        ("wVk", ctypes.c_ushort),
        ("wScan", ctypes.c_ushort),
        ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    )


class INPUT(ctypes.Structure):
    class _I(ctypes.Union):
        _fields_ = (("mi", MOUSEINPUT), ("ki", KEYBDINPUT))

    _anonymous_ = ("i",)
    _fields_ = (("type", ctypes.c_ulong), ("i", _I))


def _normalize_to_absolute(x: int, y: int) -> Tuple[int, int]:
    screen_w = user32.GetSystemMetrics(0)
    screen_h = user32.GetSystemMetrics(1)
    # Map to [0, 65535]
    nx = int(x * 65535 / max(1, screen_w - 1))
    ny = int(y * 65535 / max(1, screen_h - 1))
    return nx, ny


def _send_mouse_event(nx: int, ny: int, flags: int) -> None:
    extra = ctypes.c_ulong(0)
    mi = MOUSEINPUT(dx=nx, dy=ny, mouseData=0, dwFlags=flags, time=0, dwExtraInfo=ctypes.pointer(extra))
    inp = INPUT(type=INPUT_MOUSE, i=INPUT._I(mi=mi))
    user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(inp))


def click_absolute(x: int, y: int) -> None:
    nx, ny = _normalize_to_absolute(x, y)
    _send_mouse_event(nx, ny, MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE)
    time.sleep(0.01)
    _send_mouse_event(nx, ny, MOUSEEVENTF_LEFTDOWN | MOUSEEVENTF_ABSOLUTE)
    time.sleep(0.01)
    _send_mouse_event(nx, ny, MOUSEEVENTF_LEFTUP | MOUSEEVENTF_ABSOLUTE)


def swipe_absolute(x1: int, y1: int, x2: int, y2: int, duration_ms: int = 200) -> None:
    nx1, ny1 = _normalize_to_absolute(x1, y1)
    nx2, ny2 = _normalize_to_absolute(x2, y2)
    steps = max(2, int(duration_ms / 10))
    dx = (nx2 - nx1) / float(steps)
    dy = (ny2 - ny1) / float(steps)
    # Move to start and hold down
    _send_mouse_event(nx1, ny1, MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE)
    _send_mouse_event(nx1, ny1, MOUSEEVENTF_LEFTDOWN | MOUSEEVENTF_ABSOLUTE)
    for i in range(1, steps + 1):
        cx = int(nx1 + dx * i)
        cy = int(ny1 + dy * i)
        _send_mouse_event(cx, cy, MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE)
        time.sleep(max(0.0, duration_ms / 1000.0 / steps))
    _send_mouse_event(nx2, ny2, MOUSEEVENTF_LEFTUP | MOUSEEVENTF_ABSOLUTE)


def send_escape() -> None:
    extra = ctypes.c_ulong(0)
    ki_down = KEYBDINPUT(wVk=VK_ESCAPE, wScan=0, dwFlags=0, time=0, dwExtraInfo=ctypes.pointer(extra))
    ki_up = KEYBDINPUT(wVk=VK_ESCAPE, wScan=0, dwFlags=KEYEVENTF_KEYUP, time=0, dwExtraInfo=ctypes.pointer(extra))
    inp_down = INPUT(type=INPUT_KEYBOARD, i=INPUT._I(ki=ki_down))
    inp_up = INPUT(type=INPUT_KEYBOARD, i=INPUT._I(ki=ki_up))
    user32.SendInput(1, ctypes.byref(inp_down), ctypes.sizeof(inp_down))
    user32.SendInput(1, ctypes.byref(inp_up), ctypes.sizeof(inp_up))

