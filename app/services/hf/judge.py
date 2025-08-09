from __future__ import annotations

import json
from typing import Any, List, Tuple

from app.actions.types import BackAction, SwipeAction, TapAction, WaitAction
from app.config import settings
from app.state.encoder import GameState


class HFJudge:
    """Judge that selects the best candidate via Hugging Face (local or hosted)."""

    def __init__(self) -> None:
        self._pipeline: Any | None = None
        self._client: Any | None = None

    def _ensure_backend(self) -> None:
        model_id = settings.hf_model_id_judge
        if not model_id:
            raise RuntimeError("HF judge model id is not configured")
        if self._pipeline or self._client:
            return
        if settings.hf_inference_endpoint_url:
            from huggingface_hub import InferenceClient

            self._client = InferenceClient(
                model=model_id,
                token=settings.huggingface_hub_token,
                timeout=30,
            )
        else:
            from transformers import pipeline

            self._pipeline = pipeline(
                "text-generation",
                model=model_id,
                device_map="auto",
                torch_dtype="auto",
            )

    def _serialize_action(self, action: TapAction | SwipeAction | WaitAction | BackAction) -> dict[str, Any]:
        if isinstance(action, TapAction):
            return {"type": "tap", "x": action.x, "y": action.y}
        if isinstance(action, SwipeAction):
            return {
                "type": "swipe",
                "x1": action.x1,
                "y1": action.y1,
                "x2": action.x2,
                "y2": action.y2,
                "duration_ms": action.duration_ms,
            }
        if isinstance(action, WaitAction):
            return {"type": "wait", "seconds": action.seconds}
        if isinstance(action, BackAction):
            return {"type": "back"}
        return {"type": "unknown"}

    def _build_prompt(self, state: GameState, candidates: List[Tuple[float, Any, str]]) -> str:
        intro = (
            "You are a judge. Review candidate actions and pick the best index. Return strict JSON: {\"index\": int, \"reason\": str}.\n"
            "Rules: avoid external links/programs and avoid selling/removing heroes or equipment. Prefer safe navigation.\n"
        )
        lines = []
        for idx, (score, action, who) in enumerate(candidates):
            lines.append(
                json.dumps({
                    "i": idx,
                    "who": who,
                    "score": score,
                    "action": self._serialize_action(action),
                })
            )
        ocr = state.ocr_text[:800]
        prompt = intro + "Candidates:\n" + "\n".join(lines) + "\nOCR:\n" + ocr + "\nRespond with JSON only."
        return prompt

    def select(self, state: GameState, candidates: List[Tuple[float, Any, str]]) -> Tuple[int, str]:
        self._ensure_backend()
        prompt = self._build_prompt(state, candidates)
        raw: str
        if self._client is not None:
            raw = str(self._client.text_generation(prompt=prompt, max_new_tokens=128, temperature=0.1))  # type: ignore[no-untyped-call]
        else:
            assert self._pipeline is not None
            out = self._pipeline(prompt, max_new_tokens=128, do_sample=False)  # type: ignore[no-untyped-call]
            raw = str(out[0]["generated_text"]) if out else ""
        if not raw:
            raise RuntimeError("Empty response from HF judge")
        start = raw.find("{")
        end = raw.rfind("}")
        obj = json.loads(raw[start : end + 1])
        idx = int(obj.get("index", 0))
        reason = str(obj.get("reason", ""))
        if idx < 0 or idx >= len(candidates):
            idx = 0
        return idx, reason

