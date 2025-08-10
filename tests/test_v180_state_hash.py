from __future__ import annotations

from PIL import Image, ImageDraw

from app.state.encoder import encode_state, compute_state_hash_from_text


def _img(text: str) -> Image.Image:
  img = Image.new("RGB", (200, 100), color=(255, 255, 255))
  d = ImageDraw.Draw(img)
  d.text((5, 5), text, fill=(0, 0, 0))
  return img


def test_state_hash_present_and_stable() -> None:
  s1 = encode_state(_img("Arena Shop"))
  s2 = encode_state(_img("Arena   Shop"))
  assert s1.state_hash is not None
  assert s1.state_hash == s2.state_hash
  # compute via helper on raw text
  h = compute_state_hash_from_text("Arena Shop")
  assert h == s1.state_hash


