from __future__ import annotations

import json
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, Tuple, List

from app.config import settings


CLICKMAP_PATH = Path("data/clickmap.json")
GRID_W = max(1, int(getattr(settings, "input_base_width", 1280)))
GRID_H = max(1, int(getattr(settings, "input_base_height", 720)))
# Grid resolution (base-space pixels per cell). Coarser grid to generalize across tiny jitter
CELL = 40


@dataclass
class ClickCell:
    success: int = 0
    fail: int = 0
    last_ts: float = 0.0

    @property
    def trials(self) -> int:
        return int(self.success + self.fail)

    @property
    def score(self) -> float:
        # Smoothed success rate; unknown ~0.5 to gently explore
        total = self.trials
        if total <= 0:
            return 0.5
        return float(self.success) / float(total)


def _key_for(x: int, y: int) -> Tuple[int, int]:
    # base-space to grid cell
    return int(x // CELL), int(y // CELL)


def _center_of_cell(ix: int, iy: int) -> Tuple[int, int]:
    cx = int(ix * CELL + CELL // 2)
    cy = int(iy * CELL + CELL // 2)
    return min(GRID_W - 1, cx), min(GRID_H - 1, cy)


def load() -> Dict[str, ClickCell]:
    if not CLICKMAP_PATH.exists():
        return {}
    try:
        data = json.loads(CLICKMAP_PATH.read_text(encoding="utf-8"))
        out: Dict[str, ClickCell] = {}
        for k, v in data.items():
            out[k] = ClickCell(**{**{"success": 0, "fail": 0, "last_ts": 0.0}, **v})
        return out
    except Exception:
        return {}


def save(cm: Dict[str, ClickCell]) -> None:
    try:
        CLICKMAP_PATH.parent.mkdir(parents=True, exist_ok=True)
        obj = {k: asdict(v) for k, v in cm.items()}
        CLICKMAP_PATH.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


_clickmap_cache: Dict[str, ClickCell] | None = None


def _cm() -> Dict[str, ClickCell]:
    global _clickmap_cache
    if _clickmap_cache is None:
        _clickmap_cache = load()
    return _clickmap_cache


def record_tap_outcome(x_base: int, y_base: int, changed: bool) -> None:
    cm = _cm()
    ix, iy = _key_for(x_base, y_base)
    key = f"{ix},{iy}"
    cell = cm.get(key, ClickCell())
    if changed:
        cell.success += 1
    else:
        cell.fail += 1
    cell.last_ts = time.time()
    cm[key] = cell
    save(cm)


def click_score(x_base: int, y_base: int, radius_cells: int = 0) -> float:
    # Aggregate score in a small neighborhood to be robust to small offsets
    ix, iy = _key_for(x_base, y_base)
    scores: List[float] = []
    cm = _cm()
    for dx in range(-radius_cells, radius_cells + 1):
        for dy in range(-radius_cells, radius_cells + 1):
            key = f"{ix+dx},{iy+dy}"
            if key in cm:
                scores.append(cm[key].score)
    if not scores:
        return 0.5
    return sum(scores) / float(len(scores))


def suggest_explore_points(k: int = 5) -> List[Tuple[int, int]]:
    # Return grid centers with the fewest trials to encourage exploration
    cm = _cm()
    # Sample a coarse grid over the screen
    max_ix = max(1, GRID_W // CELL)
    max_iy = max(1, GRID_H // CELL)
    items: List[Tuple[int, int, int]] = []  # (trials, ix, iy)
    for ix in range(max_ix):
        for iy in range(max_iy):
            key = f"{ix},{iy}"
            trials = cm.get(key, ClickCell()).trials if key in cm else 0
            items.append((trials, ix, iy))
    items.sort(key=lambda t: (t[0], (t[1] - max_ix // 2) ** 2 + (t[2] - max_iy // 2) ** 2))
    pts: List[Tuple[int, int]] = []
    for _, ix, iy in items[:k]:
        pts.append(_center_of_cell(ix, iy))
    return pts


