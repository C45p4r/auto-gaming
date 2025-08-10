from __future__ import annotations

from PIL import Image, ImageDraw

from app.state.encoder import encode_state


def _img(text: str) -> Image.Image:
    img = Image.new("RGB", (300, 140), color=(255, 255, 255))
    d = ImageDraw.Draw(img)
    d.text((8, 8), text, fill=(0, 0, 0))
    return img


def test_ocr_tokens_present_and_counted() -> None:
    img = _img("Arena Battle Shop")
    st = encode_state(img)
    assert st.ocr_tokens
    assert "Arena" in st.ocr_text
    # token count feature available
    from app.state.encoder import to_features

    feats = to_features(st)
    assert feats.get("ocr_token_count", 0) >= 3


