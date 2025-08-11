from typing import Any, cast

from PIL import Image

from app.config import settings

try:
    import pytesseract as _pytesseract
except Exception:  # pragma: no cover - environment-specific import
    _pytesseract = None

# Expose a dynamically imported module as Any for typing
pytesseract: Any | None = _pytesseract


def run_ocr(image: Image.Image, lang: str | None = None, **kwargs: Any) -> str:
    if pytesseract is None:
        raise RuntimeError(
            "pytesseract is not available. Ensure it is installed and on PYTHONPATH."
        )
    # Respect explicit Tesseract binary path if provided via env/config
    if settings.tesseract_cmd:
        try:
            # pytesseract exposes a module-level variable 'tesseract_cmd'
            cast(Any, pytesseract).tesseract_cmd = settings.tesseract_cmd
        except Exception:
            pass
    language = lang or settings.ocr_language
    config = kwargs.get("config")
    text: str = cast(Any, pytesseract).image_to_string(image, lang=language, config=config)
    return text


def normalize_ocr_text(text: str) -> str:
    """Normalize OCR text for downstream parsing.

    - Unify quotes/spaces, strip non-breaking spaces
    - Collapse multiple spaces
    """
    t = text.replace("\u00A0", " ")
    t = t.replace("“", '"').replace("”", '"').replace("’", "'").replace("‘", "'")
    import re
    t = re.sub(r"\s+", " ", t)
    return t.strip()


def run_ocr_batched(image: Image.Image, tiles: tuple[int, int] = (2, 2), **kwargs: Any) -> str:
    """Run Tesseract over a grid of tiles and merge results.

    Useful as a fast path when some regions are blank/unchanged; keeps calls small.
    """
    if pytesseract is None:
        raise RuntimeError("pytesseract is not available. Ensure it is installed and on PYTHONPATH.")
    cols, rows = max(1, tiles[0]), max(1, tiles[1])
    w, h = image.size
    tw, th = w // cols, h // rows
    parts: list[str] = []
    for r in range(rows):
        for c in range(cols):
            left = c * tw
            top = r * th
            right = w if c == cols - 1 else (c + 1) * tw
            bottom = h if r == rows - 1 else (r + 1) * th
            tile = image.crop((left, top, right, bottom))
            txt: str = cast(Any, pytesseract).image_to_string(tile, lang=settings.ocr_language, config=kwargs.get("config"))
            parts.append(txt)
    merged = "\n".join(parts)
    return normalize_ocr_text(merged)
