from __future__ import annotations

import json
import math
import random
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List

from app.config import settings


@dataclass
class ArmStats:
    count: int = 0
    mean: float = 0.0


class ContextualBandit:
    """Simple per-label bandit with epsilon-greedy and running mean rewards.

    Arms are high-level targets (e.g., 'episode', 'side story', 'battle', 'hunt', 'arena', 'summon', 'shop', 'sanctuary').
    """

    def __init__(self, labels: List[str], persist_path: str | None = None) -> None:
        self.labels = labels
        self.persist_path = persist_path or settings.rl_persist_path
        self.arms: Dict[str, ArmStats] = {lbl: ArmStats() for lbl in labels}
        self._load()

    def _load(self) -> None:
        p = Path(self.persist_path)
        if not p.exists():
            return
        try:
            obj = json.loads(p.read_text(encoding="utf-8"))
            for k, v in obj.get("arms", {}).items():
                if k in self.arms:
                    self.arms[k] = ArmStats(count=int(v.get("count", 0)), mean=float(v.get("mean", 0.0)))
        except Exception:
            # ignore
            pass

    def save(self) -> None:
        try:
            Path(self.persist_path).parent.mkdir(parents=True, exist_ok=True)
            obj = {"arms": {k: asdict(v) for k, v in self.arms.items()}}
            Path(self.persist_path).write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass

    def select(self, eligible: List[str], step: int, explore_boost: float = 0.0, avoid: list[str] | None = None) -> str | None:
        if not settings.rl_enabled:
            return None
        if not eligible:
            return None
        eps0 = max(0.0, min(1.0, settings.rl_eps_start))
        eps1 = max(0.0, min(1.0, settings.rl_eps_end))
        # simple exponential decay with step proxy
        decay = 0.995 ** max(0, step)
        eps = max(eps1, min(1.0, eps0 * decay + max(0.0, min(1.0, explore_boost))))
        pool = [e for e in eligible if not avoid or e not in avoid] or eligible
        if random.random() < eps:
            return random.choice(pool)
        # exploit: pick arm with highest mean among eligible
        best = max(pool, key=lambda a: self.arms.get(a, ArmStats()).mean)
        return best

    def update(self, label: str, reward: float) -> None:
        if not settings.rl_enabled:
            return
        stats = self.arms.setdefault(label, ArmStats())
        stats.count += 1
        # running mean
        stats.mean += (reward - stats.mean) / float(stats.count)
        self.arms[label] = stats
        self.save()


