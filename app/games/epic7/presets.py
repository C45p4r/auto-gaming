from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Epic7Preset:
    name: str
    width: int
    height: int
    dpi: int
    # UI anchors in absolute pixels for this preset
    anchors: dict[str, tuple[int, int]]


DEFAULT_PRESET = Epic7Preset(
    name="e7_1080x1920",
    width=1080,
    height=1920,
    dpi=320,
    anchors={
        # Common navigation buttons
        "home_daily": (100, 1800),
        "battle": (540, 1700),
        "battle_adventure": (540, 1550),
        "battle_event": (540, 1500),
        "battle_start": (900, 1800),
        "back": (60, 100),
    },
)
