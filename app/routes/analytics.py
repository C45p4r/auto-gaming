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


@router.get("/metrics/compare")
async def compare_metrics(n: int = 5) -> dict[str, dict[str, object]]:
    """Return chunked averages and delta between last two chunks for each metric.

    Splits each metric series into n equal chunks (by index) and computes averages.
    """
    raw = store.get_series(None)
    result: dict[str, dict[str, object]] = {}
    for name, points in raw.items():
        if not points:
            continue
        k = max(1, int(n))
        size = max(1, len(points) // k)
        chunks = [points[i : i + size] for i in range(0, len(points), size)]
        chunks = chunks[-k:]  # keep only last k
        avgs: list[float] = []
        for ch in chunks:
            if not ch:
                avgs.append(0.0)
            else:
                s = sum(p.value for p in ch)
                avgs.append(float(s) / float(len(ch)))
        delta = 0.0
        if len(avgs) >= 2:
            delta = avgs[-1] - avgs[-2]
        result[name] = {"chunks": avgs, "delta": delta}
    return result
