from PIL import Image

from app.actions.types import BackAction, SwipeAction, TapAction, WaitAction
from app.policy.heuristic import propose_action
from app.safety.guards import detect_purchase_ui, screen_change
from app.state.encoder import GameState


def test_action_types_construction() -> None:
    assert TapAction(x=1, y=2).kind == "tap"
    assert SwipeAction(x1=0, y1=0, x2=10, y2=10).kind == "swipe"
    assert WaitAction(seconds=0.5).kind == "wait"
    assert BackAction().kind == "back"


def test_heuristic_policy_wait_on_low_stamina() -> None:
    state = GameState(timestamp_utc="t", stamina_current=5, stamina_cap=100, ocr_text="")
    score, action = propose_action(state)
    assert isinstance(action, WaitAction)


def test_heuristic_policy_tap_otherwise() -> None:
    state = GameState(timestamp_utc="t", stamina_current=50, stamina_cap=100, ocr_text="")
    score, action = propose_action(state)
    assert isinstance(action, TapAction)


def test_purchase_ui_detection() -> None:
    img = Image.new("RGB", (200, 80), color="white")
    # Smoke test: blank image should not trigger purchase UI detection
    assert not detect_purchase_ui(img)


def test_screen_change_bbox() -> None:
    a = Image.new("RGB", (10, 10), color="black")
    b = Image.new("RGB", (10, 10), color="black")
    b.putpixel((5, 5), (255, 255, 255))
    assert screen_change(a, b, diff_threshold=0.0)
