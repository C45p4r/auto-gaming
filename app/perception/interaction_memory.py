from __future__ import annotations

import json
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, Optional


INTERACTION_PATH = Path("data/interaction.json")


@dataclass
class ElementMemory:
    label: Optional[str]
    trials: int = 0
    success: int = 0
    last_ts: float = 0.0

    @property
    def score(self) -> float:
        if self.trials <= 0:
            return 0.5
        return float(self.success) / float(self.trials)


_cache: Dict[str, ElementMemory] | None = None


def _load() -> Dict[str, ElementMemory]:
    if not INTERACTION_PATH.exists():
        return {}
    try:
        raw = json.loads(INTERACTION_PATH.read_text(encoding="utf-8"))
        out: Dict[str, ElementMemory] = {}
        for k, v in raw.items():
            em = ElementMemory(label=v.get("label"), trials=int(v.get("trials", 0)), success=int(v.get("success", 0)), last_ts=float(v.get("last_ts", 0.0)))
            out[k] = em
        return out
    except Exception:
        return {}


def _save(obj: Dict[str, ElementMemory]) -> None:
    try:
        INTERACTION_PATH.parent.mkdir(parents=True, exist_ok=True)
        serial = {k: asdict(v) for k, v in obj.items()}
        INTERACTION_PATH.write_text(json.dumps(serial, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


def _mem() -> Dict[str, ElementMemory]:
    global _cache
    if _cache is None:
        _cache = _load()
    return _cache


def _key(label: Optional[str]) -> str:
    return (label or "__unknown__").strip().lower()


def record_element_interaction(label: Optional[str], changed: bool) -> None:
    store = _mem()
    k = _key(label)
    em = store.get(k, ElementMemory(label=label))
    em.trials += 1
    if changed:
        em.success += 1
    em.last_ts = time.time()
    store[k] = em
    _save(store)


def element_score(label: Optional[str]) -> float:
    if not label:
        return 0.5
    store = _mem()
    em = store.get(_key(label))
    return em.score if em else 0.5


