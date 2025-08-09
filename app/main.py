from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes.telemetry import router as telemetry_router


def create_app() -> FastAPI:
    app = FastAPI(title="auto-gaming", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(telemetry_router)

    return app


app = create_app()
