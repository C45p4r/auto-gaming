from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from PIL import Image

from app.perception.parser import extract_stamina, ocr_lines


@dataclass(frozen=True)
class GameState:
    timestamp_utc: str
    stamina_current: int | None
    stamina_cap: int | None
    ocr_text: str
    ocr_lines: list[str]
    ocr_tokens: list[str]


def encode_state(image: Image.Image) -> GameState:
    now = datetime.now(tz=UTC).isoformat()
    parsed = ocr_lines(image)
    stamina = extract_stamina(parsed.lines)
    cur, cap = (None, None)
    if stamina:
        cur, cap = stamina
    return GameState(
        timestamp_utc=now,
        stamina_current=cur,
        stamina_cap=cap,
        ocr_text=parsed.raw_text,
        ocr_lines=parsed.lines,
        ocr_tokens=parsed.tokens,
    )


def to_features(state: GameState) -> dict[str, Any]:
    return {
        "timestamp_utc": state.timestamp_utc,
        "stamina_current": state.stamina_current,
        "stamina_cap": state.stamina_cap,
        "has_stamina": state.stamina_current is not None and state.stamina_cap is not None,
        "ocr_token_count": len(state.ocr_tokens),
    }
