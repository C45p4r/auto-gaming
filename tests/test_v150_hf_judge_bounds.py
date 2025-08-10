from __future__ import annotations

from app.services.hf.judge import HFJudge
import pytest


def test_judge_raises_unconfigured(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.config import settings

    monkeypatch.setenv("HF_MODEL_ID_JUDGE", "")
    from importlib import reload

    reload(__import__("app.config")).config  # type: ignore[attr-defined]
    j = HFJudge()
    with pytest.raises(RuntimeError):
        j._ensure_backend()  # type: ignore[attr-defined]


