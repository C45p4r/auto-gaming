from __future__ import annotations

from app.actions.types import TapAction, WaitAction, BackAction
from app.metrics.registry import compute_metrics, score_metrics
from app.state.encoder import GameState
from app.config import settings
import random


# Sticky memory to reduce repeated tapping on unchanged scenes
_last_ocr_fingerprint: str | None = None
_repeat_count: int = 0
# Rotate through matched targets to avoid hammering a single spot
_last_choice_idx: int = -1

# Normalized targets (xFrac, yFrac) for common Epic 7 lobby menu items
_TARGETS = [
    ("episode", 0.80, 0.30),
    ("side story", 0.82, 0.35),
    ("battle", 0.83, 0.45),
    ("arena", 0.84, 0.55),
    ("summon", 0.84, 0.65),
    ("shop", 0.86, 0.75),
    ("sanctuary", 0.12, 0.28),
    ("secret shop", 0.14, 0.42),
    ("epic pass", 0.14, 0.52),
    ("event", 0.14, 0.62),
    ("epic dash", 0.16, 0.72),
]


def _fingerprint(text: str) -> str:
    t = (text or "").strip().lower()
    return t[:200]


def propose_action(state: GameState) -> tuple[float, object]:
    global _last_ocr_fingerprint, _repeat_count, _last_choice_idx
    metrics = compute_metrics(state)
    score = score_metrics(metrics)

    # Avoid hammering: back off when OCR text hasn't changed across frames
    fp = _fingerprint(state.ocr_text)
    if _last_ocr_fingerprint is not None and fp == _last_ocr_fingerprint:
        _repeat_count += 1
    else:
        _repeat_count = 0
    _last_ocr_fingerprint = fp

    if _repeat_count >= 3:
        # After repeated identical frames, first try a brief wait; occasionally send Back
        if _repeat_count % 5 == 0:
            return score, BackAction()
        return score, WaitAction(seconds=min(2.0, 0.5 + 0.3 * _repeat_count))

    # OCR-guided targeting: choose visible menu items and rotate among them
    text = (state.ocr_text or "").lower()
    matched: list[tuple[str, float, float]] = []
    for name, xf, yf in _TARGETS:
        if name in text:
            matched.append((name, xf, yf))
    if matched:
        _last_choice_idx = (_last_choice_idx + 1) % len(matched)
        _name, xf, yf = matched[_last_choice_idx]
        base_w = max(1, int(settings.input_base_width))
        base_h = max(1, int(settings.input_base_height))
        # small jitter to avoid dead pixels/overlays
        jx = (random.random() - 0.5) * 0.02  # ±2%
        jy = (random.random() - 0.5) * 0.02
        x = int((xf + jx) * base_w)
        y = int((yf + jy) * base_h)
        # keep within base bounds
        x = max(0, min(base_w - 1, x))
        y = max(0, min(base_h - 1, y))
        return score, TapAction(x=x, y=y)

    # Simple heuristic: if stamina exists and is low percentage, wait; else tap near center to advance
    if state.stamina_current is not None and state.stamina_cap:
        pct = state.stamina_current / max(1, state.stamina_cap)
        if pct < 0.1:
            return score, WaitAction(seconds=2.0)
    # Fallback: near-center tap, nudged upward 5%
    base_w = max(1, int(settings.input_base_width))
    base_h = max(1, int(settings.input_base_height))
    cx = base_w // 2
    cy = int(base_h * 0.45)
    return score, TapAction(x=cx, y=cy)
