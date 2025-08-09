from __future__ import annotations

from dataclasses import dataclass

from PIL import Image, ImageChops

from app.perception.parser import ocr_lines

PURCHASE_KEYWORDS = {
    "purchase",
    "buy",
    "limited pack",
    "monthly pass",
    "top up",
    "confirm purchase",
}


@dataclass(frozen=True)
class SafetyReport:
    purchase_ui_detected: bool
    large_screen_change: bool


def detect_purchase_ui(image: Image.Image) -> bool:
    parsed = ocr_lines(image)
    text = " ".join(parsed.lines).lower()
    return any(kw in text for kw in PURCHASE_KEYWORDS)


def screen_change(prev: Image.Image, cur: Image.Image, diff_threshold: float = 0.10) -> bool:
    if prev.size != cur.size:
        return True
    diff = ImageChops.difference(prev.convert("RGB"), cur.convert("RGB"))
    bbox = diff.getbbox()
    if not bbox:
        return False
    changed_pixels = (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])
    total_pixels = cur.size[0] * cur.size[1]
    return (changed_pixels / total_pixels) >= diff_threshold
