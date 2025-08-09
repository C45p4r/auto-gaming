from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageChops

from app.config import settings
from app.perception.parser import ocr_lines


def load_purchase_keywords() -> set[str]:
    file_path = Path(settings.safety_templates_dir) / "keywords.txt"
    if file_path.exists():
        content = file_path.read_text(encoding="utf-8")
        return {line.strip().lower() for line in content.splitlines() if line.strip()}
    # fallback defaults
    return {
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
    return detect_purchase_text(text)


def detect_purchase_text(text: str) -> bool:
    keywords = load_purchase_keywords()
    t = text.lower()
    return any(kw in t for kw in keywords)


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
