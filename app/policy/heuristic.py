from __future__ import annotations

from app.actions.types import TapAction, WaitAction
from app.metrics.registry import compute_metrics, score_metrics
from app.state.encoder import GameState


def propose_action(state: GameState) -> tuple[float, object]:
    metrics = compute_metrics(state)
    score = score_metrics(metrics)
    # Simple heuristic: if stamina exists and is low percentage, wait; else tap center to advance
    if state.stamina_current is not None and state.stamina_cap:
        pct = state.stamina_current / max(1, state.stamina_cap)
        if pct < 0.1:
            return score, WaitAction(seconds=2.0)
    return score, TapAction(x=540, y=960)
