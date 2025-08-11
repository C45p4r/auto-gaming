from __future__ import annotations

from typing import Any

from PIL import Image

from app.config import settings
from app.services.ocr.tesseract_adapter import run_ocr as tess_run, run_ocr_batched
from app.services.ocr.paddle_adapter import run_ocr as paddle_run, available as paddle_available


def run_ocr_ensemble(image: Image.Image) -> str:
    if not getattr(settings, "ocr_ensemble", True):
        return tess_run(image)
    engines = [e.strip() for e in str(getattr(settings, "ocr_engines", "tesseract,tesseract_batched,paddle")).split(",") if e.strip()]
    outputs: list[str] = []
    for e in engines:
        try:
            if e == "tesseract":
                outputs.append(tess_run(image))
            elif e == "tesseract_batched":
                outputs.append(run_ocr_batched(image))
            elif e == "paddle" and paddle_available():
                outputs.append(paddle_run(image))
        except Exception:
            continue
    # Merge by line-level voting: prefer the longest non-empty output; simplistic heuristic
    outputs = [o.strip() for o in outputs if o and o.strip()]
    if not outputs:
        return ""
    return max(outputs, key=len)


