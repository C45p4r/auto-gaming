from __future__ import annotations

import types
import pytest

from app.services.hf.policy import HFPolicy


def test_hf_policy_raises_when_unconfigured(monkeypatch: pytest.MonkeyPatch) -> None:
    # Ensure model id is empty to simulate unconfigured
    from app.config import settings

    monkeypatch.setenv("HF_MODEL_ID_POLICY", "")
    # Re-import settings so aliases update
    from importlib import reload

    reload(__import__("app.config")).config  # type: ignore[attr-defined]
    p = HFPolicy()
    with pytest.raises(RuntimeError):
        # Any fake state; method will fail before use
        p._ensure_backend()  # type: ignore[attr-defined]


