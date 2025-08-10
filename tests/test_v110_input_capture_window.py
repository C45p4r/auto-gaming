from __future__ import annotations

import types

from app.actions.executor import clamp_to_rect, compute_scaled_point


class RectObj:
    def __init__(self, left: int, top: int, width: int, height: int) -> None:
        self.left = left
        self.top = top
        self.width = width
        self.height = height
        self.right = left + width
        self.bottom = top + height


def test_compute_scaled_point_basic() -> None:
    rect = RectObj(100, 200, 1280, 720)
    # base space (1280x720) center maps to absolute center
    px, py = compute_scaled_point(1280, 720, rect, 640, 360)
    assert px == 100 + 640 and py == 200 + 360


def test_compute_scaled_point_non_uniform_scale() -> None:
    rect = RectObj(50, 80, 1920, 1080)
    px, py = compute_scaled_point(1280, 720, rect, 1280, 720)
    assert px == 50 + 1920 and py == 80 + 1080


def test_clamp_to_rect_with_margins() -> None:
    rect = RectObj(10, 20, 1000, 500)
    # A point outside on the bottom-right should be clamped inside margins
    cx, cy = clamp_to_rect(rect, 5000, 5000)
    assert rect.left < cx < rect.right
    assert rect.top < cy < rect.bottom


def test_clamp_respects_exclude_bottom() -> None:
    rect = RectObj(0, 0, 1000, 600)
    # Ask for bottom exclusion of 80px; clamped y must be <= bottom - 80
    _, cy = clamp_to_rect(rect, 9999, 9999, exclude_bottom_px=80)
    assert cy <= rect.bottom - 80


