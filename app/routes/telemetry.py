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
from pathlib import Path
import base64
from datetime import datetime
from app.diagnostics.doctor import run_self_check, suggestions_for
from app.actions.executor import execute
from app.actions.types import BackAction, WaitAction, SwipeAction
from app.agents.orchestrator import set_hf_policy_enabled, get_hf_policy_enabled
from app.telemetry.bus import bus

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


@router.get("/memory/recent")
async def memory_recent(limit: int = 20) -> list[dict[str, Any]]:
    frames_dir = Path("static/frames")
    items: list[dict[str, Any]] = []
    # Recent frames named frame_*.png with optional frame_*.json (ocr)
    pngs = sorted(frames_dir.glob("frame_*.png"), key=lambda p: p.stat().st_mtime, reverse=True)[:limit]
    for p in pngs:
        ts = p.stem.replace("frame_", "")
        ocr_path = p.with_suffix(".json")
        ocr_text = None
        if ocr_path.exists():
            try:
                import json

                o = json.loads(ocr_path.read_text(encoding="utf-8"))
                ocr_text = o.get("text")
            except Exception:
                pass
        items.append({
            "ts": ts,
            "image_url": f"/static/frames/{p.name}",
            "ocr": ocr_text,
        })
    return items


@router.get("/doctor/self-check")
async def doctor_self_check() -> dict[str, Any]:
    res = run_self_check()
    return {"ok": res.ok, "issues": res.issues, "details": res.details, "suggestions": suggestions_for(res)}


@router.post("/control/act")
async def control_act(payload: dict[str, Any] = Body(...)) -> dict[str, str]:
    """Operator one-click actions: back, wait(1s), swipe_gentle.

    Example payloads:
      {"type": "back"}
      {"type": "wait", "seconds": 1.0}
      {"type": "swipe_gentle"}
    """
    t = str(payload.get("type", "")).lower()
    if t == "back":
        execute(BackAction())
    elif t == "wait":
        seconds = float(payload.get("seconds", 1.0))
        execute(WaitAction(seconds=seconds))
    elif t == "swipe_gentle":
        base_w = max(1, int(settings.input_base_width))
        base_h = max(1, int(settings.input_base_height))
        x = int(base_w * 0.5)
        y1 = int(base_h * 0.70)
        y2 = int(base_h * 0.35)
        execute(SwipeAction(x1=x, y1=y1, x2=x, y2=y2, duration_ms=300))
    else:
        return {"status": "ignored"}
    return {"status": "ok"}


@router.post("/control/model/policy")
async def control_model_policy(payload: dict[str, Any] = Body(...)) -> dict[str, object]:
    enabled = bool(payload.get("enabled", True))
    set_hf_policy_enabled(enabled)
    return {"hf_policy_enabled": get_hf_policy_enabled()}


@router.post("/guidance/help")
async def post_help_prompt(payload: dict[str, Any] = Body(...)) -> dict[str, str | None]:
    text = str(payload.get("text", ""))
    await bus.set_help_prompt(text)
    return {"help_prompt": bus.get_help_prompt()}


@router.post("/guidance/suggest")
async def post_suggestion(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    text = str(payload.get("text", ""))
    await bus.add_suggestion(text)
    g = bus.get_guidance()
    return {"ok": True, "count": len(g.suggestions)}


@router.post("/guidance/goals")
async def post_goals(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    goals = payload.get("goals", [])
    if not isinstance(goals, list):
        goals = []
    await bus.set_goals(goals)
    return {"ok": True}


@router.post("/guidance/goals/approve")
async def post_goal_approve(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    name = str(payload.get("name", ""))
    approved = bool(payload.get("approved", True))
    await bus.approve_goal(name, approved)
    return {"ok": True}


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
