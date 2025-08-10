from __future__ import annotations

from app.policy.heuristic import propose_action
from app.state.encoder import GameState


def _mk_state(text: str) -> GameState:
    return GameState(timestamp_utc="t", stamina_current=None, stamina_cap=None, ocr_text=text, ocr_lines=[text], ocr_tokens=text.split())


def test_diverse_taps_with_matched_labels() -> None:
    s = _mk_state("Arena Battle Summon Shop")
    _, a1 = propose_action(s)
    _, a2 = propose_action(s)
    assert (getattr(a1, "x", None), getattr(a1, "y", None)) != (getattr(a2, "x", None), getattr(a2, "y", None))


def test_backoff_wait_or_back_after_repeats() -> None:
    s = _mk_state("Static Screen")
    # simulate repeats
    for _ in range(3):
        _ = propose_action(s)
    score, act = propose_action(s)
    # Expect a WaitAction or BackAction after repeated unchanged OCR
    assert act.__class__.__name__ in ("WaitAction", "BackAction")


