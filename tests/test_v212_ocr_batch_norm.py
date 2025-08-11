from __future__ import annotations

from PIL import Image, ImageDraw

from app.services.ocr.tesseract_adapter import normalize_ocr_text


def test_normalize_ocr_text_cleans_quotes_and_spaces() -> None:
    raw = "“Stamina”\u00A0: 50 / 120  "
    norm = normalize_ocr_text(raw)
    assert norm == '"Stamina" : 50 / 120'


