from __future__ import annotations

import ctypes
import time
from typing import Tuple


user32 = ctypes.windll.user32  # type: ignore[attr-defined]

# Make this process DPI aware so coordinates match real pixels on high-DPI displays
try:  # best-effort, available on Vista+
    user32.SetProcessDPIAware()
except Exception:
    pass


# Constants from WinUser.h
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_ABSOLUTE = 0x8000
MOUSEEVENTF_VIRTUALDESK = 0x4000

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
    # Use virtual screen metrics to support multi-monitor setups
    SM_XVIRTUALSCREEN = 76
    SM_YVIRTUALSCREEN = 77
    SM_CXVIRTUALSCREEN = 78
    SM_CYVIRTUALSCREEN = 79

    vs_left = user32.GetSystemMetrics(SM_XVIRTUALSCREEN)
    vs_top = user32.GetSystemMetrics(SM_YVIRTUALSCREEN)
    vs_width = user32.GetSystemMetrics(SM_CXVIRTUALSCREEN)
    vs_height = user32.GetSystemMetrics(SM_CYVIRTUALSCREEN)

    # Map to [0, 65535] across the virtual desktop
    nx = int((x - vs_left) * 65535 / max(1, vs_width - 1))
    ny = int((y - vs_top) * 65535 / max(1, vs_height - 1))
    return nx, ny


def _send_mouse_event(nx: int, ny: int, flags: int) -> None:
    extra = ctypes.c_ulong(0)
    mi = MOUSEINPUT(dx=nx, dy=ny, mouseData=0, dwFlags=flags, time=0, dwExtraInfo=ctypes.pointer(extra))
    inp = INPUT(type=INPUT_MOUSE, i=INPUT._I(mi=mi))
    user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(inp))


def click_absolute_physical(x: int, y: int) -> None:
    """Send click using direct Windows API calls - bypasses all input filtering."""
    try:
        # Get current mouse position
        current_x = ctypes.c_long()
        current_y = ctypes.c_long()
        user32.GetCursorPos(ctypes.byref(current_x), ctypes.byref(current_y))
        
        # Move mouse to target position
        user32.SetCursorPos(x, y)
        time.sleep(0.1)  # Longer delay for emulator compatibility
        
        # Perform click using direct mouse_event
        user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
        time.sleep(0.05)
        user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
        
        # Restore original mouse position
        user32.SetCursorPos(current_x.value, current_y.value)
        
    except Exception:
        # Fallback to old method if anything fails
        click_absolute_sendinput_fallback(x, y)


def click_absolute_sendinput_fallback(x: int, y: int) -> None:
    """Fallback using SendInput method."""
    nx, ny = _normalize_to_absolute(x, y)
    _send_mouse_event(nx, ny, MOUSEEVENTF_LEFTDOWN | MOUSEEVENTF_ABSOLUTE | MOUSEEVENTF_VIRTUALDESK)
    time.sleep(0.01)
    _send_mouse_event(nx, ny, MOUSEEVENTF_LEFTUP | MOUSEEVENTF_ABSOLUTE | MOUSEEVENTF_VIRTUALDESK)


def click_absolute(x: int, y: int) -> None:
    """Send click using ADB for reliable emulator input."""
    try:
        # Use ADB tap command for reliable emulator input
        click_absolute_adb(x, y)
    except Exception:
        # Fallback to physical method if ADB fails
        click_absolute_physical(x, y)


def click_absolute_adb(x: int, y: int) -> None:
    """Send click using ADB tap command."""
    import subprocess
    import os
    import logging
    
    logger = logging.getLogger(__name__)
    
    try:
        # Get Android SDK platform-tools path
        sdk_paths = [
            os.path.expanduser("~/AppData/Local/Android/Sdk/platform-tools"),
            "C:/Users/Public/AppData/Local/Android/Sdk/platform-tools",
            "C:/Program Files/Android/Android Studio/Sdk/platform-tools"
        ]
        
        adb_path = None
        for path in sdk_paths:
            potential_path = os.path.join(path, "adb.exe")
            if os.path.exists(potential_path):
                adb_path = potential_path
                break
        
        if not adb_path:
            raise FileNotFoundError(f"ADB not found in any of the expected paths: {sdk_paths}")
        
        # Execute ADB tap command
        cmd = [adb_path, "shell", "input", "tap", str(x), str(y)]
        result = subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=10)
        
        logger.info(f"ADB tap executed at ({x}, {y}) - Output: {result.stdout.strip()}")
        print(f"✅ ADB tap executed at ({x}, {y})")
        
    except subprocess.TimeoutExpired:
        error_msg = f"ADB tap timeout at ({x}, {y})"
        logger.error(error_msg)
        raise RuntimeError(error_msg)
    except subprocess.CalledProcessError as e:
        error_msg = f"ADB tap failed at ({x}, {y}): {e.stderr.strip()}"
        logger.error(error_msg)
        raise RuntimeError(error_msg)
    except Exception as e:
        error_msg = f"ADB tap error at ({x}, {y}): {e}"
        logger.error(error_msg)
        raise


def swipe_absolute(x1: int, y1: int, x2: int, y2: int, duration_ms: int = 200) -> None:
    """Send swipe using ADB for reliable emulator input."""
    try:
        # Use ADB swipe command for reliable emulator input
        swipe_absolute_adb(x1, y1, x2, y2, duration_ms)
    except Exception:
        # Fallback to physical method if ADB fails
        swipe_absolute_physical(x1, y1, x2, y2, duration_ms)


def swipe_absolute_adb(x1: int, y1: int, x2: int, y2: int, duration_ms: int = 200) -> None:
    """Send swipe using ADB swipe command."""
    import subprocess
    import os
    import logging
    
    logger = logging.getLogger(__name__)
    
    try:
        # Get Android SDK platform-tools path
        sdk_paths = [
            os.path.expanduser("~/AppData/Local/Android/Sdk/platform-tools"),
            "C:/Users/Public/AppData/Local/Android/Sdk/platform-tools",
            "C:/Program Files/Android/Android Studio/Sdk/platform-tools"
        ]
        
        adb_path = None
        for path in sdk_paths:
            potential_path = os.path.join(path, "adb.exe")
            if os.path.exists(potential_path):
                adb_path = potential_path
                break
        
        if not adb_path:
            raise FileNotFoundError(f"ADB not found in any of the expected paths: {sdk_paths}")
        
        # Execute ADB swipe command
        cmd = [adb_path, "shell", "input", "swipe", str(x1), str(y1), str(x2), str(y2), str(duration_ms)]
        result = subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=10)
        
        logger.info(f"ADB swipe executed from ({x1}, {y1}) to ({x2}, {y2}) - Output: {result.stdout.strip()}")
        print(f"✅ ADB swipe executed from ({x1}, {y1}) to ({x2}, {y2})")
        
    except subprocess.TimeoutExpired:
        error_msg = f"ADB swipe timeout from ({x1}, {y1}) to ({x2}, {y2})"
        logger.error(error_msg)
        raise RuntimeError(error_msg)
    except subprocess.CalledProcessError as e:
        error_msg = f"ADB swipe failed from ({x1}, {y1}) to ({x2}, {y2}): {e.stderr.strip()}"
        logger.error(error_msg)
        raise RuntimeError(error_msg)
    except Exception as e:
        error_msg = f"ADB swipe error from ({x1}, {y1}) to ({x2}, {y2}): {e}"
        logger.error(error_msg)
        raise


def swipe_absolute_physical(x1: int, y1: int, x2: int, y2: int, duration_ms: int = 200) -> None:
    """Perform swipe using direct Windows API calls."""
    try:
        # Get current mouse position
        current_x = ctypes.c_long()
        current_y = ctypes.c_long()
        user32.GetCursorPos(ctypes.byref(current_x), ctypes.byref(current_y))
        
        # Move to start position
        user32.SetCursorPos(x1, y1)
        time.sleep(0.1)
        
        # Press mouse button
        user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
        
        # Calculate steps
        steps = max(2, int(duration_ms / 10))
        dx = (x2 - x1) / float(steps)
        dy = (y2 - y1) / float(steps)
        
        # Move through intermediate points
        for i in range(1, steps + 1):
            cx = int(x1 + dx * i)
            cy = int(y1 + dy * i)
            user32.SetCursorPos(cx, cy)
            time.sleep(max(0.0, duration_ms / 1000.0 / steps))
        
        # Release mouse button
        user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
        
        # Restore original mouse position
        user32.SetCursorPos(current_x.value, current_y.value)
        
    except Exception:
        # Fallback to old method if anything fails
        swipe_absolute_sendinput_fallback(x1, y1, x2, y2, duration_ms)


def swipe_absolute_sendinput_fallback(x1: int, y1: int, x2: int, y2: int, duration_ms: int = 200) -> None:
    """Fallback using SendInput method."""
    nx1, ny1 = _normalize_to_absolute(x1, y1)
    nx2, ny2 = _normalize_to_absolute(x2, y2)
    steps = max(2, int(duration_ms / 10))
    dx = (nx2 - nx1) / float(steps)
    dy = (ny2 - ny1) / float(steps)
    # Move to start and hold down
    _send_mouse_event(nx1, ny1, MOUSEEVENTF_LEFTDOWN | MOUSEEVENTF_ABSOLUTE | MOUSEEVENTF_VIRTUALDESK)
    for i in range(1, steps + 1):
        cx = int(nx1 + dx * i)
        cy = int(ny1 + dy * i)
        _send_mouse_event(cx, cy, MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE | MOUSEEVENTF_VIRTUALDESK)
        time.sleep(max(0.0, duration_ms / 1000.0 / steps))
    _send_mouse_event(nx2, ny2, MOUSEEVENTF_LEFTUP | MOUSEEVENTF_ABSOLUTE | MOUSEEVENTF_VIRTUALDESK)


def send_escape() -> None:
    """Send back action using ADB keyevent."""
    try:
        # Use ADB keyevent for reliable emulator input
        send_back_adb()
    except Exception:
        # Fallback to old method if ADB fails
        send_escape_physical()


def send_back_adb() -> None:
    """Send back action using ADB keyevent."""
    import subprocess
    import os
    import logging
    
    logger = logging.getLogger(__name__)
    
    try:
        # Get Android SDK platform-tools path
        sdk_paths = [
            os.path.expanduser("~/AppData/Local/Android/Sdk/platform-tools"),
            "C:/Users/Public/AppData/Local/Android/Sdk/platform-tools",
            "C:/Program Files/Android/Android Studio/Sdk/platform-tools"
        ]
        
        adb_path = None
        for path in sdk_paths:
            potential_path = os.path.join(path, "adb.exe")
            if os.path.exists(potential_path):
                adb_path = potential_path
                break
        
        if not adb_path:
            raise FileNotFoundError(f"ADB not found in any of the expected paths: {sdk_paths}")
        
        # Execute ADB back key command
        cmd = [adb_path, "shell", "input", "keyevent", "KEYCODE_BACK"]
        result = subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=10)
        
        logger.info(f"ADB back key executed - Output: {result.stdout.strip()}")
        print("✅ ADB back key executed")
        
    except subprocess.TimeoutExpired:
        error_msg = "ADB back key timeout"
        logger.error(error_msg)
        raise RuntimeError(error_msg)
    except subprocess.CalledProcessError as e:
        error_msg = f"ADB back key failed: {e.stderr.strip()}"
        logger.error(error_msg)
        raise RuntimeError(error_msg)
    except Exception as e:
        error_msg = f"ADB back key error: {e}"
        logger.error(error_msg)
        raise


def send_escape_physical() -> None:
    """Fallback using physical key simulation."""
    extra = ctypes.c_ulong(0)
    ki_down = KEYBDINPUT(wVk=VK_ESCAPE, wScan=0, dwFlags=0, time=0, dwExtraInfo=ctypes.pointer(extra))
    ki_up = KEYBDINPUT(wVk=VK_ESCAPE, wScan=0, dwFlags=KEYEVENTF_KEYUP, time=0, dwExtraInfo=ctypes.pointer(extra))
    inp_down = INPUT(type=INPUT_KEYBOARD, i=INPUT._I(ki=ki_down))
    inp_up = INPUT(type=INPUT_KEYBOARD, i=INPUT._I(ki=ki_up))
    user32.SendInput(1, ctypes.byref(inp_down), ctypes.sizeof(inp_down))
    user32.SendInput(1, ctypes.byref(inp_up), ctypes.sizeof(inp_up))

