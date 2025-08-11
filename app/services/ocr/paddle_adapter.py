from __future__ import annotations

from typing import Any, List

from PIL import Image


def available() -> bool:
    try:
        import paddleocr  # noqa: F401
        return True
    except Exception:
        return False


def run_ocr(image: Image.Image, lang: str = "en") -> str:
    try:
        from paddleocr import PaddleOCR

        ocr = PaddleOCR(use_angle_cls=True, lang=lang)
        # PaddleOCR expects a file path or numpy array
        import numpy as np

        arr = np.array(image.convert("RGB"))
        result: List[Any] = ocr.ocr(arr, cls=True)
        lines: list[str] = []
        for page in result:
            for line in page:
                txt = line[1][0]
                if txt:
                    lines.append(str(txt))
        return "\n".join(lines)
    except Exception:
        return ""


