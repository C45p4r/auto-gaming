from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict


_PROFILE_PATH = Path("data/profile.json")


@dataclass
class ModeStatus:
    last_done_iso: str | None
    sufficient: bool


def _load() -> Dict[str, Any]:
    try:
        if _PROFILE_PATH.exists():
            return json.loads(_PROFILE_PATH.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {"modes": {}}


def _save(obj: Dict[str, Any]) -> None:
    try:
        _PROFILE_PATH.parent.mkdir(parents=True, exist_ok=True)
        _PROFILE_PATH.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


def is_mode_sufficient(mode: str) -> bool:
    data = _load()
    ms = data.get("modes", {}).get(mode, {})
    return bool(ms.get("sufficient", False))


def mark_mode_done(mode: str, sufficient: bool = False) -> None:
    data = _load()
    modes: Dict[str, Any] = data.setdefault("modes", {})
    modes[mode] = {
        "last_done_iso": datetime.now(tz=timezone.utc).isoformat(),
        "sufficient": bool(sufficient),
    }
    _save(data)


def reset_daily_if_new_day() -> None:
    data = _load()
    today = datetime.now(tz=timezone.utc).date().isoformat()
    last = data.get("last_reset_day")
    if last != today:
        # clear sufficiency flags for daily resets
        modes = data.get("modes", {})
        for m in modes.values():
            m["sufficient"] = False
        data["last_reset_day"] = today
        _save(data)


