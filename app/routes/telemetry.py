from fastapi import APIRouter

router = APIRouter(prefix="/telemetry", tags=["telemetry"])


@router.get("/ping")
async def ping() -> dict[str, str]:
    return {"pong": "ok"}
