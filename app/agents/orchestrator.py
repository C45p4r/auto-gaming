from __future__ import annotations

import asyncio
from collections.abc import Callable

from app.config import settings
from app.policy.heuristic import propose_action
from app.config import settings
from app.services.hf.policy import HFPolicy
from app.services.hf.judge import HFJudge
from app.state.encoder import GameState

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
        raise RuntimeError("No candidates after debate rounds")
    # Use HF judge if configured
    if settings.hf_model_id_judge:
        try:
            judge = HFJudge()
            idx, _reason = judge.select(state, round_candidates)
            return round_candidates[idx]
        except Exception:
            pass
    return vote(round_candidates)
