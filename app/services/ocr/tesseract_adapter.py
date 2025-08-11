from typing import Any, cast

from PIL import Image, ImageOps, ImageFilter

from app.config import settings

try:
    import pytesseract as _pytesseract
except Exception:  # pragma: no cover - environment-specific import
    _pytesseract = None

# Expose a dynamically imported module as Any for typing
pytesseract: Any | None = _pytesseract


def _preprocess(img: Image.Image) -> Image.Image:
    mode = (settings.ocr_preprocess or "auto").lower()
    scale = max(1.0, float(getattr(settings, "ocr_scale", 1.0)))
    work = img
    if scale and abs(scale - 1.0) > 1e-3:
        w, h = work.size
        work = work.resize((int(w * scale), int(h * scale)), Image.BICUBIC)
    if mode == "none":
        return work
    if mode == "grayscale" or mode == "auto":
        work = ImageOps.grayscale(work)
        work = ImageOps.autocontrast(work)
    if mode == "binary":
        work = ImageOps.grayscale(work)
        work = ImageOps.autocontrast(work)
        work = work.point(lambda p: 255 if p > 140 else 0, mode="1").convert("L")
    # very light blur to reduce aliasing
    work = work.filter(ImageFilter.MedianFilter(size=3))
    return work


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
    psm = int(getattr(settings, "ocr_psm", 6))
    oem = int(getattr(settings, "ocr_oem", 3))
    cfg = kwargs.get("config") or f"--psm {psm} --oem {oem}"
    img = _preprocess(image)
    text: str = cast(Any, pytesseract).image_to_string(img, lang=language, config=cfg)
    if getattr(settings, "ocr_multi_pass", True):
        # second pass: higher psm for sparse text
        try:
            cfg2 = f"--psm 7 --oem {oem}"
            text2: str = cast(Any, pytesseract).image_to_string(img, lang=language, config=cfg2)
            if len(text2) > len(text):
                text = text2
        except Exception:
            pass
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
