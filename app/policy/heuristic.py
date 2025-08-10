from __future__ import annotations

from app.actions.types import TapAction, WaitAction
from app.metrics.registry import compute_metrics, score_metrics
from app.state.encoder import GameState

# Sticky memory to reduce repeated tapping on unchanged scenes
_last_ocr_fingerprint: str | None = None
_repeat_count: int = 0


def _fingerprint(text: str) -> str:
    t = (text or "").strip().lower()
    return t[:200]


def propose_action(state: GameState) -> tuple[float, object]:
    global _last_ocr_fingerprint, _repeat_count
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
        # Insert a short wait to let UI change; scale mildly with repeats
        return score, WaitAction(seconds=min(2.0, 0.5 + 0.3 * _repeat_count))

    # Simple heuristic: if stamina exists and is low percentage, wait; else tap near center to advance
    if state.stamina_current is not None and state.stamina_cap:
        pct = state.stamina_current / max(1, state.stamina_cap)
        if pct < 0.1:
            return score, WaitAction(seconds=2.0)
    # Nudge toward true center but away from potential navigation bars by 5% vertically
    return score, TapAction(x=540, y=int(960 * 0.95))
