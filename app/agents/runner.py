from __future__ import annotations

import asyncio
import time
from typing import Literal, Optional
import logging
import contextlib

from PIL import Image
from pathlib import Path

from app.config import settings
from app.services.capture import capture_frame
from app.services.capture.window_manage import (
    find_window_handle,
    move_resize,
    set_topmost,
)
from app.state.encoder import encode_state
from app.agents.orchestrator import orchestrate
from app.actions.executor import execute
from app.telemetry.bus import bus
from app.safety.guards import detect_external_navigation_text, detect_item_change_text
from app.services.search.web_ingest import fetch_urls, summarize
from app.memory.store import MemoryStore, Fact
from app.metrics.registry import compute_metrics
from app.analytics.metrics import store as metrics_store
from app.analytics.session import session, Step
from app.reliability.flake import FlakeTracker


RunState = Literal["idle", "running", "paused", "stopped"]


class AgentRunner:
    def __init__(self) -> None:
        self._state: RunState = "idle"
        self._task: Optional[asyncio.Task[None]] = None
        self._pause_event = asyncio.Event()
        self._pause_event.set()  # not paused
        self._last_enforce_ts: float = 0.0
        self._last_resize_ts: float = 0.0
        self._did_initial_enforce: bool = False
        self._last_ocr_fp: str | None = None
        self._unchanged_count: int = 0
        # counters for UI stats
        self._frames: int = 0
        self._actions: int = 0
        self._taps: int = 0
        self._swipes: int = 0
        self._backs: int = 0
        self._blocks: int = 0
        self._stuck_events: int = 0
        self._last_fps_time: float = time.perf_counter()
        self._fps: float = 0.0
        self._actions_at_last_fps: int = 0
        self._window_ok: bool = False
        self._flake = FlakeTracker()

    def get_state(self) -> RunState:
        return self._state

    async def start(self) -> None:
        if self._task and not self._task.done():
            # If paused, resume
            self._pause_event.set()
            self._state = "running"
            await bus.publish_status(task="running", confidence=None, next_step=None, extra={"agent_state": self._state, **self._static_env_extra()})
            return

        self._state = "running"
        self._pause_event.set()
        self._task = asyncio.create_task(self._run_loop())
        await bus.publish_status(task="running", confidence=None, next_step=None, extra={"agent_state": self._state, **self._static_env_extra()})

    async def pause(self) -> None:
        if self._state == "running":
            self._pause_event.clear()
            self._state = "paused"
            await bus.publish_status(task="paused", confidence=None, next_step=None, extra={"agent_state": self._state})

    async def stop(self) -> None:
        if self._task and not self._task.done():
            self._task.cancel()
            with contextlib.suppress(Exception):
                await self._task
        self._state = "stopped"
        self._task = None
        self._pause_event.set()
        await bus.publish_status(task="stopped", confidence=None, next_step=None, extra={"agent_state": self._state})

    async def _run_loop(self) -> None:
        interval = 1.0 / float(settings.capture_fps)
        prev: Optional[Image.Image] = None
        consec_errors = 0
        logger = logging.getLogger("runner")
        while True:
            # Respect pause
            await self._pause_event.wait()

            # Optional window enforcement for stable capture (only once, then rarely)
            if settings.window_enforce_topmost:
                now = time.perf_counter()
                try:
                    hwnd = find_window_handle(settings.window_title_hint)
                    self._window_ok = True
                    if not self._did_initial_enforce:
                        set_topmost(hwnd, True)
                        move_resize(
                            hwnd,
                            left=int(settings.window_left),
                            top=int(settings.window_top),
                            width=int(settings.window_client_width),
                            height=int(settings.window_client_height),
                            client_area=True,
                        )
                        self._did_initial_enforce = True
                        self._last_enforce_ts = now
                        self._last_resize_ts = now
                    else:
                        # Re-apply topmost every 60s, resize every 300s to avoid flicker
                        if (now - self._last_enforce_ts) > 60.0:
                            set_topmost(hwnd, True)
                            self._last_enforce_ts = now
                        if (now - self._last_resize_ts) > 300.0:
                            move_resize(
                                hwnd,
                                left=int(settings.window_left),
                                top=int(settings.window_top),
                                width=int(settings.window_client_width),
                                height=int(settings.window_client_height),
                                client_area=True,
                            )
                            self._last_resize_ts = now
                except Exception:
                    # best-effort: continue
                    self._window_ok = False
                    pass

            start_time = time.perf_counter()

            # Capture and decide
            try:
                await bus.publish_step("capture:start", {"note": "capturing frame"})
                image = capture_frame()
                await bus.publish_step("capture:end", {"size": getattr(image, 'size', None)})
                state = encode_state(image)
                await bus.publish_step("ocr", {"text": (state.ocr_text or "")[:400]})
                # counters
                self._frames += 1
                now_fps = time.perf_counter()
                dt = now_fps - self._last_fps_time
                if dt >= 1.0:
                    self._fps = self._frames / dt
                    self._frames = 0
                    # metrics: fps and actions_per_s
                    try:
                        metrics_store.add_point("fps", self._fps)
                        actions_delta = max(0, self._actions - self._actions_at_last_fps)
                        actions_per_s = actions_delta / dt if dt > 0 else 0.0
                        metrics_store.add_point("actions_per_s", actions_per_s)
                        self._actions_at_last_fps = self._actions
                    except Exception:
                        pass
                    self._last_fps_time = now_fps
                # Track OCR stability to avoid repeating same actions
                fp = (state.ocr_text or "").strip().lower()[:200]
                if self._last_ocr_fp is not None and fp == self._last_ocr_fp:
                    self._unchanged_count += 1
                else:
                    self._unchanged_count = 0
                self._last_ocr_fp = fp

                # Store a lightweight observation of the current screen into memory for recall
                try:
                    metrics = compute_metrics(state)
                    title = f"obs:{metrics.get('screen_kind','unknown')}:{int(time.time())}"
                    summary = (state.ocr_text or "")[:300]
                    mem = MemoryStore()
                    mem.add_facts([Fact(id=None, title=title, source_url="local:ocr", summary=summary)])
                except Exception:
                    pass
                # External navigation guard: block actions if UI suggests leaving the game
                if detect_external_navigation_text(state.ocr_text):
                    self._blocks += 1
                    self._blocks += 1
                    try:
                        metrics_store.add_point("blocks", float(self._blocks))
                    except Exception:
                        pass
                    await bus.publish_status(
                        task="blocked_external_navigation",
                        confidence=None,
                        next_step="BackAction",
                        extra=self._stats_extra(),
                    )
                    # Send a back action to dismiss external prompts if not dry-run
                    if not settings.dry_run:
                        from app.actions.types import BackAction

                        execute(BackAction())
                        self._backs += 1
                    consec_errors = 0
                    continue

                # Item change guard: block any sell/remove/unequip flows until policy is mature
                if settings.hard_block_item_changes and detect_item_change_text(state.ocr_text):
                    self._blocks += 1
                    self._blocks += 1
                    try:
                        metrics_store.add_point("blocks", float(self._blocks))
                    except Exception:
                        pass
                    await bus.publish_status(
                        task="blocked_item_change",
                        confidence=None,
                        next_step="BackAction",
                        extra=self._stats_extra(),
                    )
                    if not settings.dry_run:
                        from app.actions.types import BackAction

                        execute(BackAction())
                        self._backs += 1
                    consec_errors = 0
                    continue

                # If errors or UI unchanged for several frames, try minimal web search to enrich memory
                if consec_errors >= 2 or self._unchanged_count >= 3:
                    self._stuck_events += 1
                    try:
                        metrics_store.add_point("stuck_events", float(self._stuck_events))
                    except Exception:
                        pass
                    try:
                        hints = [line for line in state.ocr_text.splitlines() if line.strip()][:3]
                        await bus.publish_step("stuck:search:start", {"hints": hints})
                        # Simple Google queries; relies on fetch_urls to rate-limit politely
                        queries = [f"https://www.google.com/search?q=Epic7%20{h}" for h in hints]
                        docs = fetch_urls(queries[:2])
                        mem = MemoryStore()
                        facts = [
                            Fact(id=None, title=d.title, source_url=d.url, summary=summarize(d))
                            for d in docs
                        ]
                        if facts:
                            mem.add_facts(facts)
                        await bus.publish_step("stuck:search:end", {"facts": [f.title for f in facts]})
                    except Exception:
                        pass

                decide_t0 = time.perf_counter()
                score, action, who = await orchestrate(state)
                await bus.publish_step("policy", {"who": who, "score": score, "action": action.__class__.__name__})
                await bus.publish_status(
                    task=f"{who} proposing action",
                    confidence=float(score),
                    next_step=action.__class__.__name__,
                    extra=self._stats_extra(),
                )
                # Save recent frame snapshot to static/frames with OCR JSON for Memory tab
                try:
                    frames_dir = Path("static/frames")
                    frames_dir.mkdir(parents=True, exist_ok=True)
                    stamp = int(time.time() * 1000)
                    img_path = frames_dir / f"frame_{stamp}.png"
                    image.save(img_path)
                    import json

                    (frames_dir / f"frame_{stamp}.json").write_text(
                        json.dumps({"text": state.ocr_text or ""}, ensure_ascii=False, indent=2),
                        encoding="utf-8",
                    )
                except Exception:
                    pass
                if not settings.dry_run:
                    execute(action)
                    # naive action counters by class name
                    name = action.__class__.__name__
                    self._actions += 1
                    if name == "TapAction":
                        self._taps += 1
                    elif name == "SwipeAction":
                        self._swipes += 1
                    elif name == "BackAction":
                        self._backs += 1
                # publish decision log with context
                try:
                    ocr_fp = (state.ocr_text or "").strip().lower()[:120]
                    latency_ms = (time.perf_counter() - decide_t0) * 1000.0
                    try:
                        metrics_store.add_point("decision_latency_ms", float(latency_ms))
                    except Exception:
                        pass
                    # minimal metric deltas placeholder (0) until we compute before/after deltas
                    await bus.publish_decision(
                        action={"type": name, **getattr(action, "__dict__", {})},
                        reason=f"{who} selected with score={score:.2f}",
                        metric_deltas={},
                        who=who,
                        success=True,
                        latency_ms=latency_ms,
                        ocr_fp=ocr_fp,
                        metrics={},
                    )
                    # Append to session replay log (reference saved frame path if available)
                    try:
                        session.add(
                            Step(
                                ts=time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()),
                                action=name,
                                reason=f"{who}:{score:.2f}",
                                image_path=str(img_path) if 'img_path' in locals() else None,
                            )
                        )
                    except Exception:
                        pass
                except Exception:
                    pass
                consec_errors = 0
            except Exception as exc:
                logger.exception("runner_loop_error")
                consec_errors += 1
                # Track reliability flake events
                try:
                    self._flake.record_error(self._last_ocr_fp)
                except Exception:
                    pass
                backoff = float(settings.error_backoff_s) * min(4.0, 1.0 + consec_errors / 2.0)
                # surface the error briefly to UI
                try:
                    await bus.publish_status(task="error", confidence=None, next_step=str(exc)[:200], extra=self._stats_extra())
                except Exception:
                    pass
                await asyncio.sleep(backoff)
                if consec_errors >= int(settings.max_consec_errors):
                    try:
                        await bus.publish_status(task="error_quit", confidence=None, next_step=str(exc)[:200], extra=self._stats_extra())
                    except Exception:
                        pass
                    break
            prev = image

            elapsed = time.perf_counter() - start_time
            # If in quarantine mode due to flakiness, slow down slightly
            slow = 0.3 if getattr(self._flake, "in_quarantine", False) else 0.0
            await asyncio.sleep(max(0.0, interval - elapsed + slow))


runner = AgentRunner()

    def _stats_extra(self) -> dict[str, float | int]:
        return {
            "fps": round(self._fps, 2),
            "actions": self._actions,
            "taps": self._taps,
            "swipes": self._swipes,
            "backs": self._backs,
            "blocks": self._blocks,
            "stuck_events": self._stuck_events,
            "window_ok": 1 if self._window_ok else 0,
            **self._static_env_extra(),
        }

    def _static_env_extra(self) -> dict[str, str | bool]:
        try:
            return {
                "capture_backend": str(settings.capture_backend or "auto"),
                "input_backend": str(settings.input_backend or "auto"),
                "window_enforce_topmost": bool(settings.window_enforce_topmost),
                "window_title_hint": str(settings.window_title_hint or ""),
                "model_policy": "hf-policy" if settings.hf_model_id_policy else "policy-lite",
                "model_id_policy": str(settings.hf_model_id_policy or ""),
                "model_id_judge": str(settings.hf_model_id_judge or ""),
            }
        except Exception:
            return {}

