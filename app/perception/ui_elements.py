from dataclasses import dataclass
from typing import List, Sequence
from PIL import Image

# Heuristic UI button detector using normalized anchor positions
# Anchors are based on 1280x720 Epic7 lobby layout; we scale to current image size


@dataclass(frozen=True)
class UiButton:
    label: str | None
    x: int
    y: int
    w: int
    h: int


@dataclass(frozen=True)
class ResourceCounter:
    name: str
    value: int


# label, x_frac, y_frac, w_frac, h_frac
_KNOWN_BUTTONS: list[tuple[str, float, float, float, float]] = [
    ("episode", 0.80, 0.30, 0.10, 0.08),
    ("side story", 0.82, 0.35, 0.12, 0.08),
    ("battle", 0.83, 0.45, 0.10, 0.08),
    ("arena", 0.84, 0.55, 0.10, 0.08),
    ("summon", 0.84, 0.65, 0.12, 0.08),
    ("shop", 0.86, 0.75, 0.10, 0.08),
    ("event", 0.14, 0.62, 0.12, 0.10),
    ("sanctuary", 0.12, 0.28, 0.12, 0.10),
]


def detect_ui_buttons(image: Image.Image, ocr_text: str, ocr_tokens: Sequence[str] | None = None) -> List[UiButton]:
    text = (ocr_text or "").lower()
    token_set = set((ocr_tokens or []))
    w, h = image.size
    found: list[UiButton] = []
    for label, xf, yf, wf, hf in _KNOWN_BUTTONS:
        if (label in text) or (label in token_set):
            cx = int(xf * w)
            cy = int(yf * h)
            bw = max(8, int(wf * w))
            bh = max(8, int(hf * h))
            x = max(0, min(w - 1, cx - bw // 2))
            y = max(0, min(h - 1, cy - bh // 2))
            found.append(UiButton(label=label, x=x, y=y, w=bw, h=bh))
    return found
