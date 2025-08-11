import json
import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from app.config import settings
from app.telemetry.bus import bus


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": self.formatTime(record, datefmt="%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(level: str | None = None) -> None:
    Path(settings.logs_dir).mkdir(parents=True, exist_ok=True)

    root = logging.getLogger()
    lvl = (level or settings.log_level or "INFO").upper()
    root.setLevel(lvl)

    stdout_handler = logging.StreamHandler(stream=sys.stdout)
    json_formatter = JsonFormatter()
    stdout_handler.setFormatter(json_formatter)

    file_handler = RotatingFileHandler(
        str(Path(settings.logs_dir) / "app.log"), maxBytes=5_000_000, backupCount=3
    )
    file_handler.setFormatter(json_formatter)

    # Clear existing handlers to avoid duplicates when reloading (e.g., uvicorn reload)
    root.handlers = []
    root.addHandler(stdout_handler)
    root.addHandler(file_handler)

    # Mirror logs to telemetry bus for UI if enabled
    if getattr(settings, "log_to_ws", True):
        class WSHandler(logging.Handler):
            def emit(self, record: logging.LogRecord) -> None:  # type: ignore[override]
                try:
                    # Avoid await in handler; schedule fire-and-forget
                    import asyncio
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        loop.create_task(bus.publish_log(record.levelname, record.name, record.getMessage()))
                except Exception:
                    pass

        ws_handler = WSHandler()
        ws_handler.setLevel(lvl)
        root.addHandler(ws_handler)
