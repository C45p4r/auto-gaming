from __future__ import annotations

import asyncio
import time
from typing import Literal, Optional
import logging
import contextlib

from PIL import Image

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

    def get_state(self) -> RunState:
        return self._state

    async def start(self) -> None:
        if self._task and not self._task.done():
            # If paused, resume
            self._pause_event.set()
            self._state = "running"
            await bus.publish_status(task="running", confidence=None, next_step=None, extra={"agent_state": self._state})
            return

        self._state = "running"
        self._pause_event.set()
        self._task = asyncio.create_task(self._run_loop())
        await bus.publish_status(task="running", confidence=None, next_step=None, extra={"agent_state": self._state})

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
                    pass

            start_time = time.perf_counter()

            # Capture and decide
            try:
                image = capture_frame()
                state = encode_state(image)
                # counters
                self._frames += 1
                now_fps = time.perf_counter()
                dt = now_fps - self._last_fps_time
                if dt >= 1.0:
                    self._fps = self._frames / dt
                    self._frames = 0
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
                        hints = [line for line in state.ocr_text.splitlines() if line.strip()][:3]
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
                    except Exception:
                        pass

                decide_t0 = time.perf_counter()
                score, action, who = await orchestrate(state)
                await bus.publish_status(
                    task=f"{who} proposing action",
                    confidence=float(score),
                    next_step=action.__class__.__name__,
                    extra=self._stats_extra(),
                )
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
                except Exception:
                    pass
                consec_errors = 0
            except Exception as exc:
                logger.exception("runner_loop_error")
                consec_errors += 1
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
            await asyncio.sleep(max(0.0, interval - elapsed))


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
        }

