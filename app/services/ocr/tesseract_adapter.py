from typing import Any

import pytesseract
from PIL import Image

from app.config import settings


def run_ocr(image: Image.Image, lang: str | None = None, **kwargs: Any) -> str:
    language = lang or settings.ocr_language
    config = kwargs.get("config")
    return pytesseract.image_to_string(image, lang=language, config=config)


