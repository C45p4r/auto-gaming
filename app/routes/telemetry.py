from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.memory.store import MemoryStore
from app.telemetry.bus import Guidance, bus

router = APIRouter(prefix="/telemetry", tags=["telemetry"])


@router.get("/ping")
async def ping() -> dict[str, str]:
    return {"pong": "ok"}


@router.get("/status")
async def status() -> dict[str, Any]:
    return bus.get_status()


@router.get("/decisions")
async def decisions() -> list[dict[str, Any]]:
    return bus.get_decision_log()


@router.post("/guidance")
async def guidance(payload: Guidance) -> dict[str, str]:
    await bus.set_guidance(payload)
    return {"ok": "true"}


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
