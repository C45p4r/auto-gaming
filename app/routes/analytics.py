from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query, Body

from app.analytics.metrics import store
from app.analytics.session import session

router = APIRouter(prefix="/analytics", tags=["analytics"])


_DEFAULT_QUERY = Query(default=None)


@router.get("/metrics")
async def get_metrics(names: list[str] | None = _DEFAULT_QUERY) -> dict[str, Any]:
    data = store.get_series(names)
    # convert dataclasses
    return {k: [p.__dict__ for p in v] for k, v in data.items()}


@router.get("/session")
async def get_session() -> list[dict[str, Any]]:
    return [s.__dict__ for s in session.all()]


@router.get("/session/export")
async def export_session() -> str:
    return session.to_jsonl()


@router.post("/session/import")
async def import_session(jsonl: str = Body(..., embed=True)) -> dict[str, int]:
    n = session.replace_from_jsonl(jsonl)
    return {"steps": n}
