from __future__ import annotations

import asyncio
from contextlib import suppress
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from pathlib import Path
import json


@dataclass
class DecisionLogEntry:
    timestamp_utc: str
    action: dict[str, Any]
    reason: str
    metric_deltas: dict[str, float]
    who: str
    success: bool
    latency_ms: float
    ocr_fp: str
    metrics: dict[str, float]


@dataclass
class Guidance:
    prioritize: list[str] = field(default_factory=list)
    avoid: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    goals: list[dict] = field(default_factory=list)


class TelemetryBus:
    def __init__(self) -> None:
        self._subscribers: set[asyncio.Queue[dict[str, Any]]] = set()
        self._status: dict[str, Any] = {"task": None, "confidence": None, "next": None}
        self._decision_log: list[DecisionLogEntry] = []
        self._log_ring: list[dict[str, Any]] = []
        self._guidance_path = Path("data/guidance.json")
        self._guidance: Guidance = self._load_guidance() or Guidance(
            goals=[
                {"name": "Complete daily quests", "approved": True},
                {"name": "Maximize resources (stamina, gold)", "approved": True},
                {"name": "Unlock/upgrade characters", "approved": True},
                {"name": "Obtain strong equipment", "approved": True},
                {"name": "Arena progress", "approved": False},
                {"name": "Event participation", "approved": True},
            ]
        )
        self._lock = asyncio.Lock()
        self._help_prompt: str | None = None

    async def subscribe(self) -> asyncio.Queue[dict[str, Any]]:
        q: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        async with self._lock:
            self._subscribers.add(q)
        await q.put({"type": "status", "data": self._status})
        return q

    async def unsubscribe(self, q: asyncio.Queue[dict[str, Any]]) -> None:
        async with self._lock:
            self._subscribers.discard(q)

    async def _broadcast(self, message: dict[str, Any]) -> None:
        async with self._lock:
            for q in list(self._subscribers):
                with suppress(Exception):
                    q.put_nowait(message)

    async def publish_log(self, level: str, logger: str, msg: str) -> None:
        item = {
            "timestamp_utc": datetime.now(tz=UTC).isoformat(),
            "level": level,
            "logger": logger,
            "msg": msg,
        }
        self._log_ring.append(item)
        try:
            from app.config import settings as _settings
            self._log_ring = self._log_ring[-int(getattr(_settings, "log_ring_size", 1000)) :]
        except Exception:
            self._log_ring = self._log_ring[-1000:]
        await self._broadcast({"type": "log", "data": item})

    async def publish_status(
        self,
        task: str | None,
        confidence: float | None,
        next_step: str | None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        base = {"task": task, "confidence": confidence, "next": next_step}
        if extra:
            base.update(extra)
        self._status = base
        await self._broadcast({"type": "status", "data": self._status})

    async def publish_decision(
        self,
        action: dict[str, Any],
        reason: str,
        metric_deltas: dict[str, float],
        who: str,
        success: bool,
        latency_ms: float,
        ocr_fp: str,
        metrics: dict[str, float] | None = None,
    ) -> None:
        entry = DecisionLogEntry(
            timestamp_utc=datetime.now(tz=UTC).isoformat(),
            action=action,
            reason=reason,
            metric_deltas=metric_deltas,
            who=who,
            success=success,
            latency_ms=float(latency_ms),
            ocr_fp=ocr_fp,
            metrics=metrics or {},
        )
        self._decision_log.append(entry)
        self._decision_log = self._decision_log[-200:]
        await self._broadcast({"type": "decision", "data": entry.__dict__})

    async def publish_step(self, kind: str, payload: dict[str, Any]) -> None:
        msg = {
            "type": "step",
            "data": {
                "timestamp_utc": datetime.now(tz=UTC).isoformat(),
                "kind": kind,
                "payload": payload,
            },
        }
        await self._broadcast(msg)

    async def set_guidance(self, guidance: Guidance) -> None:
        self._guidance = guidance
        self._save_guidance()
        await self._broadcast({"type": "guidance", "data": self._guidance.__dict__})

    def get_status(self) -> dict[str, Any]:
        return self._status

    def get_decision_log(self) -> list[dict[str, Any]]:
        return [e.__dict__ for e in self._decision_log]

    def recent_logs(self, limit: int = 200) -> list[dict[str, Any]]:
        return list(self._log_ring[-int(limit) :])

    def get_guidance(self) -> Guidance:
        return self._guidance

    async def set_help_prompt(self, prompt: str | None) -> None:
        self._help_prompt = (prompt or "").strip() or None
        self._save_guidance()
        await self._broadcast({"type": "guidance", "data": {**self._guidance.__dict__, "help_prompt": self._help_prompt}})

    def get_help_prompt(self) -> str | None:
        return self._help_prompt

    async def add_suggestion(self, text: str) -> None:
        t = (text or "").strip()
        if not t:
            return
        # keep last 20 suggestions
        self._guidance.suggestions.append(t)
        self._guidance.suggestions = self._guidance.suggestions[-20:]
        self._save_guidance()
        await self._broadcast({"type": "guidance", "data": self._guidance.__dict__})

    async def set_goals(self, goals: list[dict]) -> None:
        # Sanitize: expect items with name and approved
        cleaned: list[dict] = []
        for g in goals:
            name = str(g.get("name", "")).strip()
            if not name:
                continue
            cleaned.append({"name": name, "approved": bool(g.get("approved", True))})
        self._guidance.goals = cleaned
        self._save_guidance()
        await self._broadcast({"type": "guidance", "data": self._guidance.__dict__})

    async def approve_goal(self, name: str, approved: bool) -> None:
        name = name.strip()
        if not name:
            return
        found = False
        for g in self._guidance.goals:
            if str(g.get("name", "")).strip().lower() == name.lower():
                g["approved"] = bool(approved)
                found = True
                break
        if not found:
            self._guidance.goals.append({"name": name, "approved": bool(approved)})
        self._save_guidance()
        await self._broadcast({"type": "guidance", "data": self._guidance.__dict__})

    # Persistence helpers
    def _load_guidance(self) -> Guidance | None:
        try:
            if self._guidance_path.exists():
                obj = json.loads(self._guidance_path.read_text(encoding="utf-8"))
                g = Guidance(
                    prioritize=list(obj.get("prioritize", [])),
                    avoid=list(obj.get("avoid", [])),
                    suggestions=list(obj.get("suggestions", []))[:20],
                    goals=list(obj.get("goals", [])),
                )
                self._help_prompt = obj.get("help_prompt")
                return g
        except Exception:
            return None
        return None

    def _save_guidance(self) -> None:
        try:
            self._guidance_path.parent.mkdir(parents=True, exist_ok=True)
            obj = {**self._guidance.__dict__, "help_prompt": self._help_prompt}
            self._guidance_path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass


bus = TelemetryBus()
