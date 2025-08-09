from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

ActionKind = Literal["tap", "swipe", "wait", "back"]


@dataclass(frozen=True)
class TapAction:
    kind: ActionKind = "tap"
    x: int = 0
    y: int = 0


@dataclass(frozen=True)
class SwipeAction:
    kind: ActionKind = "swipe"
    x1: int = 0
    y1: int = 0
    x2: int = 0
    y2: int = 0
    duration_ms: int = 300


@dataclass(frozen=True)
class WaitAction:
    kind: ActionKind = "wait"
    seconds: float = 1.0


@dataclass(frozen=True)
class BackAction:
    kind: ActionKind = "back"


Action = TapAction | SwipeAction | WaitAction | BackAction
