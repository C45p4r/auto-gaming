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
