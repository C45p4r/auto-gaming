from __future__ import annotations

from app.actions.types import TapAction, WaitAction, BackAction, SwipeAction
from app.metrics.registry import compute_metrics, score_metrics
from app.state.encoder import GameState
from app.config import settings
from app.state.profile import is_mode_sufficient, mark_mode_done, reset_daily_if_new_day
import random


# Sticky memory to reduce repeated tapping on unchanged scenes
_last_ocr_fingerprint: str | None = None
_repeat_count: int = 0
# Track per-label cooldown to avoid immediate re-taps on the same menu label
_label_cooldown: dict[str, int] = {}
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


def _fingerprint(text: str, tokens: list[str] | None = None) -> str:
    # Normalize OCR text aggressively to detect "same screen" despite small OCR jitter
    t = (text or "").lower()
    # Keep letters and spaces only; collapse spaces
    cleaned = []
    prev_space = False
    for ch in t:
        if ch.isalpha():
            cleaned.append(ch)
            prev_space = False
        elif ch.isspace():
            if not prev_space:
                cleaned.append(" ")
            prev_space = True
        # drop digits/punctuations
    norm = ("".join(cleaned)).strip()
    # Focus on presence of key labels to be robust
    keys = [
        "episode",
        "side story",
        "battle",
        "arena",
        "summon",
        "shop",
        "event",
        "sanctuary",
    ]
    present = []
    base = norm
    for k in keys:
        if k in norm:
            present.append(k)
    if tokens:
        token_set = set(tokens)
        for k in keys:
            if k in token_set and k not in present:
                present.append(k)
    if present:
        present.sort()
        base = "|".join(present)
    return base[:200]


def propose_action(state: GameState) -> tuple[float, object]:
    global _last_ocr_fingerprint, _repeat_count, _last_choice_idx
    # Reset daily sufficiency flags if a new day
    reset_daily_if_new_day()
    metrics = compute_metrics(state)
    score = score_metrics(metrics)
    # Bias toward progress: small preference for moving toward common progression menus
    progress_keywords = ("episode", "battle", "quest", "event", "summon", "shop", "arena")
    text_lower = (state.ocr_text or "").lower()
    if any(k in text_lower for k in progress_keywords):
        score += 0.05

    # Avoid hammering: back off when OCR text hasn't changed across frames
    fp = _fingerprint(state.ocr_text, state.ocr_tokens)
    if _last_ocr_fingerprint is not None and fp == _last_ocr_fingerprint:
        _repeat_count += 1
    else:
        _repeat_count = 0
    _last_ocr_fingerprint = fp

    if _repeat_count >= 2:
        # Progressive backoff ladder: wait → back → gentle swipes (up/down) → wait
        step = _repeat_count % 6
        base_w = max(1, int(settings.input_base_width))
        base_h = max(1, int(settings.input_base_height))
        if step == 2:
            return score, WaitAction(seconds=0.8)
        if step == 3:
            return score, BackAction()
        if step == 4:
            x = int(base_w * 0.50)
            y1 = int(base_h * 0.70)
            y2 = int(base_h * 0.35)
            return score, SwipeAction(x1=x, y1=y1, x2=x, y2=y2, duration_ms=320)
        if step == 5:
            x = int(base_w * 0.50)
            y1 = int(base_h * 0.35)
            y2 = int(base_h * 0.70)
            return score, SwipeAction(x1=x, y1=y1, x2=x, y2=y2, duration_ms=320)
        return score, WaitAction(seconds=0.5)

    # OCR-guided targeting: choose visible menu items and rotate among them
    text = (state.ocr_text or "").lower()
    # If we see locked cues, put a long cooldown on 'arena'
    if any(s in text for s in ("rookie arena", "unlock after", "arena locked")):
        _label_cooldown["arena"] = max(_label_cooldown.get("arena", 0), 20)
    # quick path: if tokens available, build a set for O(1) contains
    token_set = set((state.ocr_tokens or []))
    matched: list[tuple[str, float, float]] = []
    for name, xf, yf in _TARGETS:
        if (name in text) or (name in token_set):
            # Skip arena if on long cooldown due to lock
            if name == "arena" and _label_cooldown.get("arena", 0) > 0:
                continue
            matched.append((name, xf, yf))
    if matched:
        # Filter out labels on cooldown
        ready = [t for t in matched if _label_cooldown.get(t[0], 0) <= 0] or matched
        _last_choice_idx = (_last_choice_idx + 1) % len(ready)
        name, xf, yf = ready[_last_choice_idx]
        # If a mode is already considered sufficient today, deprioritize by small bias
        if is_mode_sufficient(name):
            score -= 0.03
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
        # Set a short cooldown to avoid immediate re-selection
        _label_cooldown[name] = max(3, _label_cooldown.get(name, 0))
        # Decay existing cooldowns
        for k in list(_label_cooldown.keys()):
            _label_cooldown[k] = max(0, _label_cooldown[k] - 1)
        return score, TapAction(x=x, y=y)

    # Simple heuristic: if stamina exists and is low percentage, wait; else tap near center to advance
    if state.stamina_current is not None and state.stamina_cap:
        pct = state.stamina_current / max(1, state.stamina_cap)
        if pct < 0.1:
            return score, WaitAction(seconds=2.0)
    # Fallback exploration: tap in a horizontal exploration band (30%-60% height)
    base_w = max(1, int(settings.input_base_width))
    base_h = max(1, int(settings.input_base_height))
    x = int(base_w * (0.35 + random.random() * 0.30))
    y = int(base_h * (0.30 + random.random() * 0.30))
    return score, TapAction(x=x, y=y)
