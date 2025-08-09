from __future__ import annotations

import asyncio
import time
from typing import Literal, Optional
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


RunState = Literal["idle", "running", "paused", "stopped"]


class AgentRunner:
    def __init__(self) -> None:
        self._state: RunState = "idle"
        self._task: Optional[asyncio.Task[None]] = None
        self._pause_event = asyncio.Event()
        self._pause_event.set()  # not paused

    def get_state(self) -> RunState:
        return self._state

    async def start(self) -> None:
        if self._task and not self._task.done():
            # If paused, resume
            self._pause_event.set()
            self._state = "running"
            await bus.publish_status(task="running", confidence=None, next_step=None)
            return

        self._state = "running"
        self._pause_event.set()
        self._task = asyncio.create_task(self._run_loop())
        await bus.publish_status(task="running", confidence=None, next_step=None)

    async def pause(self) -> None:
        if self._state == "running":
            self._pause_event.clear()
            self._state = "paused"
            await bus.publish_status(task="paused", confidence=None, next_step=None)

    async def stop(self) -> None:
        if self._task and not self._task.done():
            self._task.cancel()
            with contextlib.suppress(Exception):
                await self._task
        self._state = "stopped"
        self._task = None
        self._pause_event.set()
        await bus.publish_status(task="stopped", confidence=None, next_step=None)

    async def _run_loop(self) -> None:
        interval = 1.0 / float(settings.capture_fps)
        prev: Optional[Image.Image] = None
        consec_errors = 0
        while True:
            # Respect pause
            await self._pause_event.wait()

            # Optional window enforcement for stable capture
            if settings.window_enforce_topmost:
                try:
                    hwnd = find_window_handle(settings.window_title_hint)
                    set_topmost(hwnd, True)
                    move_resize(
                        hwnd,
                        left=int(settings.window_left),
                        top=int(settings.window_top),
                        width=int(settings.window_client_width),
                        height=int(settings.window_client_height),
                        client_area=True,
                    )
                except Exception:
                    # best-effort: continue
                    pass

            start_time = time.perf_counter()

            # Capture and decide
            try:
                image = capture_frame()
                state = encode_state(image)
                # External navigation guard: block actions if UI suggests leaving the game
                if detect_external_navigation_text(state.ocr_text):
                    await bus.publish_status(
                        task="blocked_external_navigation",
                        confidence=None,
                        next_step="BackAction",
                    )
                    # Send a back action to dismiss external prompts if not dry-run
                    if not settings.dry_run:
                        from app.actions.types import BackAction

                        execute(BackAction())
                    consec_errors = 0
                    continue

                # Item change guard: block any sell/remove/unequip flows until policy is mature
                if settings.hard_block_item_changes and detect_item_change_text(state.ocr_text):
                    await bus.publish_status(
                        task="blocked_item_change",
                        confidence=None,
                        next_step="BackAction",
                    )
                    if not settings.dry_run:
                        from app.actions.types import BackAction

                        execute(BackAction())
                    consec_errors = 0
                    continue

                # If stuck recently, try minimal web search to enrich memory
                if consec_errors >= 2:
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

                score, action, who = await orchestrate(state)
                await bus.publish_status(
                    task=f"{who} proposing action",
                    confidence=float(score),
                    next_step=action.__class__.__name__,
                )
                if not settings.dry_run:
                    execute(action)
                consec_errors = 0
            except Exception:
                consec_errors += 1
                backoff = float(settings.error_backoff_s) * min(4.0, 1.0 + consec_errors / 2.0)
                await asyncio.sleep(backoff)
                if consec_errors >= int(settings.max_consec_errors):
                    await bus.publish_status(task="error_quit", confidence=None, next_step=None)
                    break
            prev = image

            elapsed = time.perf_counter() - start_time
            await asyncio.sleep(max(0.0, interval - elapsed))


runner = AgentRunner()

