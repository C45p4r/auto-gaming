from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Body

from app.memory.store import MemoryStore
from app.telemetry.bus import Guidance, bus
from app.agents.runner import runner
from app.services.capture.window_manage import (
    find_window_handle,
    get_client_rect,
    move_resize,
    set_topmost,
)
from app.config import settings

router = APIRouter(prefix="/telemetry", tags=["telemetry"])


@router.get("/ping")
async def ping() -> dict[str, str]:
    return {"pong": "ok"}


@router.get("/status")
async def status() -> dict[str, Any]:
    data = bus.get_status()
    return {"agent_state": runner.get_state(), **data}


@router.get("/decisions")
async def decisions() -> list[dict[str, Any]]:
    return bus.get_decision_log()


@router.post("/guidance")
async def guidance(payload: Guidance) -> dict[str, str]:
    await bus.set_guidance(payload)
    return {"ok": "true"}


@router.post("/control/start")
async def control_start() -> dict[str, str]:
    await runner.start()
    return {"state": runner.get_state()}


@router.post("/control/pause")
async def control_pause() -> dict[str, str]:
    await runner.pause()
    return {"state": runner.get_state()}


@router.post("/control/stop")
async def control_stop() -> dict[str, str]:
    await runner.stop()
    return {"state": runner.get_state()}


@router.get("/memory/search")
async def memory_search(q: str) -> list[dict[str, Any]]:
    store = MemoryStore()
    results = store.search(q)
    return [r.__dict__ for r in results]


@router.websocket("/ws")
async def ws_endpoint(ws: WebSocket) -> None:
    await ws.accept()
    q = await bus.subscribe()
    try:
        while True:
            # push telemetry
            try:
                msg = await asyncio.wait_for(q.get(), timeout=0.5)
                await ws.send_json(msg)
            except TimeoutError:
                pass
            # receive optional messages (ignored for now)
            try:
                recv = await asyncio.wait_for(ws.receive_text(), timeout=0.01)
                # future: process client messages
                _ = recv
            except TimeoutError:
                pass
    except WebSocketDisconnect:
        await bus.unsubscribe(q)


@router.get("/window/rect")
async def window_rect() -> dict[str, int]:
    """Return current emulator client-area rectangle in screen coordinates."""
    hwnd = find_window_handle(settings.window_title_hint)
    r = get_client_rect(hwnd)
    return {"left": r.left, "top": r.top, "width": r.width, "height": r.height}


@router.post("/window/set")
async def window_set(
    left: int = Body(...), top: int = Body(...), width: int = Body(...), height: int = Body(...)
) -> dict[str, int]:
    """Move/resize emulator to desired client-area rectangle."""
    hwnd = find_window_handle(settings.window_title_hint)
    set_topmost(hwnd, True)
    move_resize(hwnd, left=left, top=top, width=width, height=height, client_area=True)
    r = get_client_rect(hwnd)
    return {"left": r.left, "top": r.top, "width": r.width, "height": r.height}
