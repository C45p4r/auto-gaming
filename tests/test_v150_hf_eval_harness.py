from __future__ import annotations

from typing import Any, Tuple

from app.services.hf.policy import HFPolicy
from app.state.encoder import GameState
import pytest


def _state(ocr: str) -> GameState:
    return GameState(timestamp_utc="t", stamina_current=None, stamina_cap=None, ocr_text=ocr, ocr_lines=ocr.split(), ocr_tokens=ocr.split())


def test_eval_hf_policy_parse_error_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    p = HFPolicy()

    def bad_backend(self: HFPolicy) -> None:
        # Inject a dummy pipeline that returns non-JSON text
        class Dummy:
            def __call__(self, prompt: str, max_new_tokens: int, do_sample: bool) -> list[dict[str, Any]]:
                return [{"generated_text": "nonsense without json"}]

        self._pipeline = Dummy()

    monkeypatch.setattr(HFPolicy, "_ensure_backend", bad_backend)
    with pytest.raises(Exception):
        p.propose(_state("Arena Shop"))


