from __future__ import annotations

import asyncio
from collections.abc import Callable

from app.config import settings
from app.policy.heuristic import propose_action
from app.config import settings
from app.services.hf.policy import HFPolicy
from app.services.hf.judge import HFJudge
from app.state.encoder import GameState
from app.state.profile import is_mode_locked
from app.telemetry.bus import bus
from app.memory.store import MemoryStore

Candidate = tuple[float, object, str]


async def run_with_timeout(fn: Callable[[], Candidate], timeout_s: float) -> Candidate | None:
    loop = asyncio.get_event_loop()
    try:
        return await asyncio.wait_for(loop.run_in_executor(None, fn), timeout=timeout_s)
    except Exception:
        return None


_hf_policy: HFPolicy | None = None
_hf_policy_enabled: bool = True


def set_hf_policy_enabled(enabled: bool) -> None:
    global _hf_policy_enabled
    _hf_policy_enabled = bool(enabled)


def get_hf_policy_enabled() -> bool:
    return _hf_policy_enabled


def agent_policy(state: GameState) -> Candidate:
    global _hf_policy
    # Try HF policy if configured
    if settings.hf_model_id_policy and _hf_policy_enabled:
        try:
            if _hf_policy is None:
                _hf_policy = HFPolicy()
            proposal = _hf_policy.propose(state)
            return proposal.score, proposal.action, "hf-policy"
        except Exception:
            pass
    # Fallback to heuristic
    score, action = propose_action(state)
    # Penalize actions that target a locked mode if we can infer from ui_buttons
    try:
        label = None
        if hasattr(action, "x") and hasattr(action, "y") and getattr(state, "ui_buttons", None) and state.img_width and state.img_height:
            # Find nearest known button center to the proposed tap
            ax = int(getattr(action, "x"))
            ay = int(getattr(action, "y"))
            # convert base coords to image coords
            ix = int(ax / max(1, int(settings.input_base_width)) * state.img_width)
            iy = int(ay / max(1, int(settings.input_base_height)) * state.img_height)
            best_d = 1e9
            for b in state.ui_buttons:
                cx = b.x + b.w // 2
                cy = b.y + b.h // 2
                d = (cx - ix) ** 2 + (cy - iy) ** 2
                if d < best_d:
                    best_d = d
                    label = b.label
        if label and is_mode_locked(label):
            score -= 0.2
    except Exception:
        pass
    return score, action, "policy-lite"


def agent_mechanics(state: GameState) -> Candidate:
    # Placeholder for a different reasoning angle
    score, action = propose_action(state)
    return score * 0.99, action, "mechanics-expert"


def agent_guide_reader(state: GameState) -> Candidate:
    score, action = propose_action(state)
    return score * 0.98, action, "guide-reader"


def vote(candidates: list[Candidate]) -> Candidate:
    # If HF judge is configured, defer selection
    if settings.hf_model_id_judge:
        try:
            judge = HFJudge()
            # We need a GameState to include OCR in the prompt; here we fallback to local vote.
            # The orchestrate() caller has the state; so judge integration will happen there instead.
        except Exception:
            pass
    # Weighted by score; break ties by fixed priority
    if not candidates:
        raise RuntimeError("No candidates proposed")
    return max(candidates, key=lambda c: c[0])


async def orchestrate(state: GameState) -> Candidate:
    # Learning-first: consult memory before proposing actions to bias away from known dead-ends
    try:
        store = MemoryStore()
        hints = (state.ocr_text or "").strip().splitlines()
        query = " ".join(hints[:2]) or ("|".join(state.ocr_tokens[:6]) if state.ocr_tokens else "")
        if query:
            facts = store.search(query, top_k=5)
            # Surface to UI for transparency
            await bus.publish_step("memory:search", {"query": query[:120], "top": [f.title for f in facts[:3]]})
            # If any fact indicates a lock for a known label, downweight that path globally during this orchestration
            locked_labels = [
                f.title.split(":")[-1]
                for f in facts
                if any(s in f.summary.lower() for s in ("locked", "unlock after", "you can enter after")) and f.title.startswith("ui:button:")
            ]
            if locked_labels:
                # Publish as context; heuristic already respects is_mode_locked; this is a soft nudge
                await bus.publish_step("memory:locked_labels", {"labels": locked_labels[:5]})
    except Exception:
        pass
    agents: list[Callable[[], Candidate]] = [
        lambda: agent_policy(state),
        lambda: agent_mechanics(state),
        lambda: agent_guide_reader(state),
    ][: settings.max_agents]

    round_candidates: list[Candidate] = []
    for _ in range(max(1, settings.debate_rounds)):
        tasks = [run_with_timeout(fn, settings.agent_timeout_s) for fn in agents]
        results = await asyncio.gather(*tasks)
        candidates = [r for r in results if r is not None]
        if not candidates:
            continue
        # simple critique pass could adjust scores; here pass-through
        round_candidates.extend(candidates)

    if not round_candidates:
        # Fallback: ask for help prompt if available; otherwise tap exploration band
        help_text = bus.get_guidance().prioritize if hasattr(bus, "get_guidance") else []
        # provide a minimal safe fallback action
        from app.actions.types import TapAction
        base_w =  max(1, int(getattr(__import__('app.config').config.settings, 'input_base_width', 1280)))
        base_h =  max(1, int(getattr(__import__('app.config').config.settings, 'input_base_height', 720)))
        import random
        x = int(base_w * (0.35 + random.random() * 0.30))
        y = int(base_h * (0.30 + random.random() * 0.30))
        return 0.1, TapAction(x=x, y=y), "fallback"
    # Use HF judge if configured
    if settings.hf_model_id_judge:
        try:
            judge = HFJudge()
            idx, _reason = judge.select(state, round_candidates)
            return round_candidates[idx]
        except Exception:
            pass
    return vote(round_candidates)
