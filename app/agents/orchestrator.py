from __future__ import annotations

import asyncio
from collections.abc import Callable

from app.config import settings
from app.policy.heuristic import propose_action
from app.perception.clickmap import click_score, suggest_explore_points
from app.config import settings
from app.services.hf.policy import HFPolicy
from app.services.hf.judge import HFJudge
from app.state.encoder import GameState
from app.state.profile import is_mode_locked
from app.telemetry.bus import bus
from app.memory.store import MemoryStore, Fact
from app.services.search.web_ingest import fetch_urls, summarize

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
    # Adjust score using clickmap knowledge: boost likely-buttons, nudge unknowns, penalize static
    try:
        if hasattr(action, "x") and hasattr(action, "y"):
            ax = int(getattr(action, "x"))
            ay = int(getattr(action, "y"))
            s = click_score(ax, ay, radius_cells=1)
            # Map score in [0,1] to adjustment around 0: unknown ~0.5 => ~0 bonus
            adj = (s - 0.5) * 0.2  # ±0.1 max
            score = float(score) + adj
    except Exception:
        pass
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
    # Learning-first: consult memory before proposing actions to bias away from known dead-ends;
    # optionally enrich memory via lightweight web search if nothing relevant is found
    try:
        store = MemoryStore()
        hints = (state.ocr_text or "").strip().splitlines()
        query = " ".join(hints[:2]) or ("|".join(state.ocr_tokens[:6]) if state.ocr_tokens else "")
        mem_prefer: set[str] = set()
        mem_discourage: set[str] = set()
        facts: list[Fact] = []
        if query:
            # Run memory search in parallel with agent proposals
            mem_task = asyncio.to_thread(store.search, query, 5)
        else:
            mem_task = None
        # We will await mem_task below after proposals are started
    except Exception:
        mem_task = None  # type: ignore
        mem_prefer, mem_discourage = set(), set()
    def _infer_label_from_action(action: object) -> str | None:
        try:
            if hasattr(state, "ui_buttons") and state.ui_buttons and hasattr(action, "x") and hasattr(action, "y") and state.img_width and state.img_height:
                ax = int(getattr(action, "x"))
                ay = int(getattr(action, "y"))
                ix = int(ax / max(1, int(settings.input_base_width)) * state.img_width)
                iy = int(ay / max(1, int(settings.input_base_height)) * state.img_height)
                best_d = 1e9
                best_label = None
                for b in state.ui_buttons:
                    cx = b.x + b.w // 2
                    cy = b.y + b.h // 2
                    d = (cx - ix) ** 2 + (cy - iy) ** 2
                    if d < best_d:
                        best_d = d
                        best_label = b.label
                return best_label
        except Exception:
            return None
        return None

    agents: list[Callable[[], Candidate]] = [
        lambda: agent_policy(state),
        lambda: agent_mechanics(state),
        lambda: agent_guide_reader(state),
    ][: settings.max_agents]

    round_candidates: list[Candidate] = []
    for _ in range(max(1, settings.debate_rounds)):
        tasks = [run_with_timeout(fn, settings.agent_timeout_s) for fn in agents]
        # Await candidates and, if present, memory results concurrently
        if mem_task is not None:
            results, facts = await asyncio.gather(asyncio.gather(*tasks), mem_task)
            await bus.publish_step("memory:search", {"query": (query or "")[:120], "top": [f.title for f in facts[:3]]})
            if not facts and query:
                # Try web enrichment without blocking too long
                try:
                    qwords = (state.ocr_tokens or [])[:5]
                    q = "Epic Seven " + " ".join(qwords)
                    seeds = [
                        f"https://duckduckgo.com/html/?q={q}",
                        f"https://www.google.com/search?q={q}",
                    ]
                    new_docs = await asyncio.to_thread(fetch_urls, seeds)
                    new_facts = [Fact(id=None, title=d.title, source_url=d.url, summary=summarize(d)) for d in new_docs[:2]]
                    if new_facts:
                        store.add_facts(new_facts)
                        await bus.publish_step("memory:web:add", {"added": [f.title for f in new_facts]})
                        facts = store.search(query, top_k=5)
                except Exception:
                    pass
        else:
            results = await asyncio.gather(*tasks)
        candidates = [r for r in results if r is not None]
        # Adjust scores based on memory-derived preferences
        adjusted: list[Candidate] = []
        try:
            for f in facts:
                tl = f.title.lower()
                summ = f.summary.lower()
                for lbl in ("episode", "side story", "battle", "shop", "summon", "event", "sanctuary", "hunt", "arena"):
                    if lbl in tl or lbl in summ:
                        if any(s in summ for s in ("locked", "unlock after", "you can enter after")):
                            mem_discourage.add(lbl)
                        else:
                            mem_prefer.add(lbl)
        except Exception:
            pass
        for sc, act, who in candidates:
            lbl = _infer_label_from_action(act)
            bonus = 0.0
            if lbl and lbl in mem_prefer:
                bonus += 0.05
            if lbl and lbl in mem_discourage:
                bonus -= 0.08
            adjusted.append((float(sc) + bonus, act, who))
        candidates = adjusted
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
        # Prefer low-trial cells from clickmap to encourage discovering buttons
        pts = suggest_explore_points(k=5)
        if pts:
            cx, cy = random.choice(pts)
            x, y = int(cx), int(cy)
        else:
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
