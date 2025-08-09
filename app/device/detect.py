from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass


def _adb(args: list[str], timeout: float = 10.0) -> str:
    proc = subprocess.run(["adb", *args], capture_output=True, text=True, timeout=timeout)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or "adb command failed")
    return proc.stdout.strip()


@dataclass(frozen=True)
class DisplayInfo:
    width: int
    height: int
    physical_density: int | None
    override_density: int | None
    orientation: str  # portrait|landscape|unknown


def get_display_info() -> DisplayInfo:
    size_out = _adb(["shell", "wm", "size"])  # e.g., "Physical size: 1080x1920"
    density_out = _adb(["shell", "wm", "density"])  # may include override & physical
    rot_out = _adb(["shell", "dumpsys", "input"])  # find SurfaceOrientation

    m = re.search(r"(Physical size|Override size):\s*(\d+)x(\d+)", size_out)
    if not m:
        # Fallback via dumpsys display
        disp = _adb(["shell", "dumpsys", "display"]).replace("\r", "")
        m2 = re.search(r"mBaseDisplayInfo.*?\s(\d+) x (\d+)", disp)
        w, h = (int(m2.group(1)), int(m2.group(2))) if m2 else (0, 0)
    else:
        w, h = int(m.group(2)), int(m.group(3))

    phys_d = None
    over_d = None
    mp = re.search(r"Physical density:\s*(\d+)", density_out)
    mo = re.search(r"Override density:\s*(\d+)", density_out)
    if mp:
        phys_d = int(mp.group(1))
    if mo:
        over_d = int(mo.group(1))

    # Orientation
    ori = "unknown"
    mo = re.search(r"SurfaceOrientation:\s*(\d)", rot_out)
    if mo:
        val = int(mo.group(1))
        # 0=portrait, 1=landscape, 2=reverse-portrait, 3=reverse-landscape
        ori = "landscape" if val in (1, 3) else "portrait"
    else:
        if w > 0 and h > 0:
            ori = "landscape" if w > h else "portrait"

    return DisplayInfo(
        width=w,
        height=h,
        physical_density=phys_d,
        override_density=over_d,
        orientation=ori,
    )


@dataclass(frozen=True)
class DeviceDoctorReport:
    display: DisplayInfo
    suitable: bool
    suggestions: list[str]
    chosen_preset: str | None


def doctor_for_epic7(display: DisplayInfo) -> DeviceDoctorReport:
    suggestions: list[str] = []
    chosen: str | None = None

    # Prefer 1080x1920 portrait or 1920x1080 landscape with density 320
    wants_w, wants_h, wants_dpi = 1080, 1920, 320
    fits_res = sorted((display.width, display.height)) == sorted((wants_w, wants_h))
    fits_dpi = (display.override_density or display.physical_density) == wants_dpi
    is_land = display.orientation == "landscape"

    if not fits_res:
        suggestions.append("Set resolution to 1080x1920: adb shell wm size 1080x1920")
    if not fits_dpi:
        suggestions.append("Set density override to 320: adb shell wm density 320")
    if not is_land:
        suggestions.append(
            "Rotate to landscape (toolbar rotate) or run: "
            "adb shell settings put system accelerometer_rotation 0 "
            "&& adb shell settings put system user_rotation 1"
        )

    if fits_res:
        chosen = "epic7_1080x1920"

    suitable = fits_res and is_land
    return DeviceDoctorReport(
        display=display, suitable=suitable, suggestions=suggestions, chosen_preset=chosen
    )


def apply_basic_fixes_for_epic7(report: DeviceDoctorReport) -> list[str]:
    applied: list[str] = []
    for s in report.suggestions:
        if "wm size" in s:
            _adb(["shell", "wm", "size", "1080x1920"])  # set size
            applied.append("set size 1080x1920")
        elif "wm density" in s:
            _adb(["shell", "wm", "density", "320"])  # set density
            applied.append("set density 320")
        elif "user_rotation" in s:
            _adb(
                [
                    "shell",
                    "settings",
                    "put",
                    "system",
                    "accelerometer_rotation",
                    "0",
                ]
            )  # disable auto-rotate
            applied.append("disable auto-rotate")
            _adb(
                [
                    "shell",
                    "settings",
                    "put",
                    "system",
                    "user_rotation",
                    "1",
                ]
            )  # force landscape
            applied.append("force landscape")
    return applied
