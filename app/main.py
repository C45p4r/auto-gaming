import logging
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from app.routes.analytics import router as analytics_router
from app.routes.telemetry import router as telemetry_router
from app.logging_config import configure_logging


def create_app() -> FastAPI:
    configure_logging()
    app = FastAPI(title="auto-gaming", version="1.0.0-beta")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def access_log(request: Request, call_next):
        # Temporarily disable custom access logging to avoid formatter conflicts.
        # We still have JSON root logs and runner logs in logs/app.log.
        response = await call_next(request)
        return response

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    # Serve static assets (e.g., recent screenshots for Memory tab)
    static_dir = Path("static")
    (static_dir / "frames").mkdir(parents=True, exist_ok=True)
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    app.include_router(telemetry_router)
    app.include_router(analytics_router)

    return app


app = create_app()
