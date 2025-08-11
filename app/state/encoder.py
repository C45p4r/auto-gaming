from __future__ import annotations

from dataclasses import dataclass
import hashlib
from datetime import UTC, datetime
from typing import Any

from PIL import Image
from typing import List

from app.perception.parser import extract_stamina, ocr_lines, ParsedText
from app.perception.ui_elements import UiButton, detect_ui_buttons


@dataclass(frozen=True)
class GameState:
    timestamp_utc: str
    stamina_current: int | None
    stamina_cap: int | None
    ocr_text: str
    ocr_lines: list[str]
    ocr_tokens: list[str]
    state_hash: str | None = None
    ui_buttons: List[UiButton] | None = None
    img_width: int | None = None
    img_height: int | None = None


def encode_state(image: Image.Image) -> GameState:
    now = datetime.now(tz=UTC).isoformat()
    parsed = ocr_lines(image)
    stamina = extract_stamina(parsed.lines)
    cur, cap = (None, None)
    if stamina:
        cur, cap = stamina
    # compute a simple content hash over tokens for caching/replay
    token_str = "|".join(parsed.tokens).lower()
    sh = hashlib.sha1(token_str.encode("utf-8")).hexdigest() if token_str else None
    # detect common UI buttons/icons to help targeting
    try:
        buttons = detect_ui_buttons(image, parsed.raw_text, parsed.tokens)
    except Exception:
        buttons = []
    return GameState(
        timestamp_utc=now,
        stamina_current=cur,
        stamina_cap=cap,
        ocr_text=parsed.raw_text,
        ocr_lines=parsed.lines,
        ocr_tokens=parsed.tokens,
        state_hash=sh,
        ui_buttons=buttons,
        img_width=image.size[0] if image else None,
        img_height=image.size[1] if image else None,
    )


def to_features(state: GameState) -> dict[str, Any]:
    return {
        "timestamp_utc": state.timestamp_utc,
        "stamina_current": state.stamina_current,
        "stamina_cap": state.stamina_cap,
        "has_stamina": state.stamina_current is not None and state.stamina_cap is not None,
        "ocr_token_count": len(state.ocr_tokens),
        "state_hash": state.state_hash,
    }


def compute_state_hash_from_text(text: str) -> str:
    tokens = [t for t in text.lower().split() if t]
    token_str = "|".join(tokens)
    return hashlib.sha1(token_str.encode("utf-8")).hexdigest()


def encode_state_parsed(parsed: ParsedText) -> GameState:
    now = datetime.now(tz=UTC).isoformat()
    stamina = extract_stamina(parsed.lines)
    cur, cap = (None, None)
    if stamina:
        cur, cap = stamina
    token_str = "|".join(parsed.tokens).lower()
    sh = hashlib.sha1(token_str.encode("utf-8")).hexdigest() if token_str else None
    return GameState(
        timestamp_utc=now,
        stamina_current=cur,
        stamina_cap=cap,
        ocr_text=parsed.raw_text,
        ocr_lines=parsed.lines,
        ocr_tokens=parsed.tokens,
        state_hash=sh,
        ui_buttons=[],
        img_width=None,
        img_height=None,
    )
