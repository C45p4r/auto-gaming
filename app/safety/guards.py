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
    external_nav_detected: bool


def detect_purchase_ui(image: Image.Image) -> bool:
    parsed = ocr_lines(image)
    text = " ".join(parsed.lines).lower()
    return detect_purchase_text(text)


def detect_purchase_text(text: str) -> bool:
    keywords = load_purchase_keywords()
    t = text.lower()
    return any(kw in t for kw in keywords)


EXTERNAL_NAVIGATION_TERMS: set[str] = {
    "external link",
    "open browser",
    "open in browser",
    "visit website",
    "watch ad",
    "advertisement",
    "youtube",
    "facebook",
    "twitter",
    "x.com",
    "instagram",
    "discord",
}

# Add common obfuscated variants (no spaces/punctuation) to withstand OCR quirks
EXTERNAL_NAVIGATION_COMPACT: set[str] = {t.replace(" ", "").replace(".", "") for t in EXTERNAL_NAVIGATION_TERMS}


def detect_external_navigation_text(text: str) -> bool:
    t = text.lower()
    if any(term in t for term in EXTERNAL_NAVIGATION_TERMS):
        return True
    compact = "".join(ch for ch in t if ch.isalnum())
    return any(term in compact for term in EXTERNAL_NAVIGATION_COMPACT)


ITEM_CHANGE_TERMS: set[str] = {
    # conservative blocklist to avoid selling/removing heroes/equipment
    "sell",
    "discard",
    "dismantle",
    "enhance using",
    "remove equipment",
    "unequip",
    "dismiss hero",
    "retire hero",
}
ITEM_CHANGE_COMPACT: set[str] = {t.replace(" ", "") for t in ITEM_CHANGE_TERMS}


def detect_item_change_text(text: str) -> bool:
    t = text.lower()
    if any(term in t for term in ITEM_CHANGE_TERMS):
        return True
    compact = "".join(ch for ch in t if ch.isalnum())
    return any(term in compact for term in ITEM_CHANGE_COMPACT)


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
