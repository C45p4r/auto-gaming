from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Optional, Tuple

from app.actions.types import BackAction, SwipeAction, TapAction, WaitAction
from app.config import settings
from app.state.encoder import GameState


@dataclass
class HFActionProposal:
    score: float
    action: TapAction | SwipeAction | WaitAction | BackAction
    who: str = "hf-policy"


class HFPolicy:
    """Thin adapter over transformers pipeline or Hugging Face InferenceClient.

    Loads lazily on first use. Returns a structured action parsed from model output.
    Falls back to raising on any error; caller should handle fallback to heuristic.
    """

    def __init__(self) -> None:
        self._pipeline: Any | None = None
        self._client: Any | None = None

    def _ensure_backend(self) -> None:
        if self._pipeline or self._client:
            return
        model_id = settings.hf_model_id_policy
        if not model_id:
            raise RuntimeError("HF policy model id is not configured")

        if settings.hf_inference_endpoint_url:
            # Hosted inference via InferenceClient
            from huggingface_hub import InferenceClient

            self._client = InferenceClient(
                model=model_id,
                token=settings.huggingface_hub_token,
                timeout=30,
            )
        else:
            # Local transformers pipeline
            from transformers import pipeline

            self._pipeline = pipeline(
                "text-generation",
                model=model_id,
                device_map="auto",
                torch_dtype="auto",
            )

    def _build_prompt(self, state: GameState) -> str:
        base_w = settings.input_base_width
        base_h = settings.input_base_height
        guidance = (
            "Role: You are a pro Epic Seven player making optimal, safe moves.\n"
            "Primary objectives: maximize resources, complete quests, unlock characters, obtain strong equipment, and progress menus efficiently.\n"
            "Rules: do NOT open external links/programs; do NOT sell/remove heroes or equipment; prefer safe navigation steps."
        )
        return (
            "You control a mobile game via actions. Propose ONE next action as strict JSON, no prose.\n"
            "Allowed actions (choose one):\n"
            "- Tap: {\"type\":\"tap\", \"x\": int[0..%d], \"y\": int[0..%d]}\n"
            "- Swipe: {\"type\":\"swipe\", \"x1\":int, \"y1\":int, \"x2\":int, \"y2\":int, \"duration_ms\":int[50..1200]}\n"
            "- Wait: {\"type\":\"wait\", \"seconds\": float[0.2..2.0]}\n"
            "- Back: {\"type\":\"back\"}\n"
            f"{guidance}\n"
            "Recent OCR text from screen (may be noisy):\n" + state.ocr_text[:1000] + "\n"
            "Return ONLY the JSON object."
        ) % (base_w, base_h)

    def _parse_action(self, raw: str) -> Tuple[float, TapAction | SwipeAction | WaitAction | BackAction]:
        # Extract first JSON object from raw
        start = raw.find("{")
        end = raw.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise ValueError("No JSON object found in model output")
        obj = json.loads(raw[start : end + 1])
        t = str(obj.get("type", "")).lower()
        # conservative score placeholder
        score = 0.5
        if t == "tap":
            x = int(obj.get("x", 0))
            y = int(obj.get("y", 0))
            return score, TapAction(x=x, y=y)
        if t == "swipe":
            return (
                score,
                SwipeAction(
                    x1=int(obj.get("x1", 0)),
                    y1=int(obj.get("y1", 0)),
                    x2=int(obj.get("x2", 0)),
                    y2=int(obj.get("y2", 0)),
                    duration_ms=int(obj.get("duration_ms", 200)),
                ),
            )
        if t == "wait":
            return score, WaitAction(seconds=float(obj.get("seconds", 0.5)))
        if t == "back":
            return score, BackAction()
        raise ValueError(f"Unsupported action type from model: {t}")

    def propose(self, state: GameState) -> HFActionProposal:
        self._ensure_backend()
        prompt = self._build_prompt(state)
        raw: Optional[str] = None
        try:
            if self._client is not None:
                # Hosted
                raw = self._client.text_generation(prompt=prompt, max_new_tokens=128, temperature=0.2)  # type: ignore[no-untyped-call]
            elif self._pipeline is not None:
                out = self._pipeline(prompt, max_new_tokens=128, do_sample=False)  # type: ignore[no-untyped-call]
                raw = str(out[0]["generated_text"]) if out else None
            else:
                raise RuntimeError("No HF backend available")
        except Exception as e:
            # Surface a structured error for evaluation harness; caller will fallback
            raise RuntimeError(f"HF policy generation failed: {e}")

        if not raw:
            raise RuntimeError("Empty response from HF backend")

        score, action = self._parse_action(raw)
        return HFActionProposal(score=score, action=action)

