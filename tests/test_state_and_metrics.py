from PIL import Image, ImageDraw

from app.metrics.registry import compute_metrics, score_metrics
from app.state.encoder import encode_state


def _fake_image_with_text(text: str) -> Image.Image:
    img = Image.new("RGB", (400, 200), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.text((10, 10), text, fill=(0, 0, 0))
    return img


def test_encode_state_with_stamina_parses_numbers() -> None:
    img = _fake_image_with_text("Stamina: 50/120")
    state = encode_state(img)
    assert state.stamina_current == 50
    assert state.stamina_cap == 120
    assert isinstance(state.ocr_lines, list) and state.ocr_lines
    assert isinstance(state.ocr_tokens, list) and state.ocr_tokens


def test_compute_and_score_metrics() -> None:
    img = _fake_image_with_text("Stamina: 10/100")
    state = encode_state(img)
    metrics = compute_metrics(state)
    score = score_metrics(metrics)
    assert score >= 1.0  # has resource_safety == 1.0
