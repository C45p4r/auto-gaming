from __future__ import annotations

from PIL import Image

from app.safety.guards import (
    detect_external_navigation_text,
    detect_item_change_text,
    detect_purchase_text,
    screen_change,
)


def test_external_navigation_detection_keywords() -> None:
    assert detect_external_navigation_text("Open in browser?")
    assert detect_external_navigation_text("Watch ad to continue")
    assert detect_external_navigation_text("Visit website")


def test_item_change_blocklist() -> None:
    assert detect_item_change_text("Sell this item?")
    assert detect_item_change_text("Remove equipment now")


def test_purchase_detection_defaults() -> None:
    assert detect_purchase_text("Confirm purchase of monthly pass")
    assert detect_purchase_text("Limited Pack available")


def test_screen_change_metric() -> None:
    img1 = Image.new("RGB", (100, 50), color=(0, 0, 0))
    img2 = Image.new("RGB", (100, 50), color=(0, 0, 0))
    assert screen_change(img1, img2) is False
    # change half the image
    img2.paste((255, 255, 255), (0, 0, 50, 50))
    assert screen_change(img1, img2, diff_threshold=0.40) is True


