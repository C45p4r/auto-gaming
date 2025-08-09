import json
import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from app.config import settings


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


def configure_logging(level: str = "INFO") -> None:
    Path(settings.logs_dir).mkdir(parents=True, exist_ok=True)

    root = logging.getLogger()
    root.setLevel(level.upper())

    stdout_handler = logging.StreamHandler(stream=sys.stdout)
    json_formatter = JsonFormatter()
    stdout_handler.setFormatter(json_formatter)

    file_handler = RotatingFileHandler(
        str(Path(settings.logs_dir) / "app.log"), maxBytes=5_000_000, backupCount=3
    )
    file_handler.setFormatter(json_formatter)

    # Clear existing handlers to avoid duplicates when reloading
    root.handlers = []
    root.addHandler(stdout_handler)
    root.addHandler(file_handler)
