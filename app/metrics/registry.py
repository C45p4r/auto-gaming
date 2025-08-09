from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from app.state.encoder import GameState


@dataclass(frozen=True)
class Metrics:
    daily_progress: float
    resource_safety: float
    farm_efficiency: float
    arena_focus: float


def compute_metrics(state: GameState) -> Metrics:
    # Simplified initial metrics using stamina presence as proxy
    has_stamina = (state.stamina_current is not None) and (state.stamina_cap is not None)
    resource_safety = 1.0 if has_stamina else 0.0
    # Placeholders; to be refined with real signals
    return Metrics(
        daily_progress=0.0,
        resource_safety=resource_safety,
        farm_efficiency=0.0,
        arena_focus=0.0,
    )


def metric_weights() -> Mapping[str, float]:
    # weights from environment; fall back to defaults
    return {
        "daily_progress": 1.0,
        "resource_safety": 1.0,
        "farm_efficiency": 1.0,
        "arena_focus": 1.0,
    }


def score_metrics(metrics: Metrics) -> float:
    weights = metric_weights()
    score = (
        metrics.daily_progress * weights["daily_progress"]
        + metrics.resource_safety * weights["resource_safety"]
        + metrics.farm_efficiency * weights["farm_efficiency"]
        + metrics.arena_focus * weights["arena_focus"]
    )
    return float(score)
