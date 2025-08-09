from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass

from PIL import Image

from app.services.ocr.tesseract_adapter import run_ocr


@dataclass(frozen=True)
class ParsedText:
    raw_text: str
    lines: list[str]


def ocr_lines(image: Image.Image) -> ParsedText:
    text = run_ocr(image)
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    return ParsedText(raw_text=text, lines=lines)


STAMINA_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"^stamina\s*[:：]\s*(\d+)/(\d+)$", re.I),
    re.compile(r"^(\d+)/(\d+)\s*stamina$", re.I),
]


def extract_stamina(lines: Iterable[str]) -> tuple[int, int] | None:
    for line in lines:
        for pat in STAMINA_PATTERNS:
            m = pat.search(line)
            if m:
                cur = int(m.group(1))
                cap = int(m.group(2))
                return cur, cap
    return None
