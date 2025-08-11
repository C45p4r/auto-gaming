from __future__ import annotations

import pytest

from app.actions.executor import compute_scaled_point


class RectObj:
    def __init__(self, left: int, top: int, width: int, height: int):
        self.left = left
        self.top = top
        self.width = width
        self.height = right = left + width
        self.bottom = top + height


def test_compute_scaled_point():
    # Test window rect (882x496 client area)
    rect = RectObj(100, 200, 882, 496)
    # base space (882x496) center maps to absolute center
    px, py = compute_scaled_point(882, 496, rect, 441, 248)
    assert px == 541  # 100 + 441
    assert py == 448  # 200 + 248

    # Test edge case: base space max coords
    px, py = compute_scaled_point(882, 496, rect, 882, 496)
    assert px == 982  # 100 + 882
    assert py == 696  # 200 + 496


