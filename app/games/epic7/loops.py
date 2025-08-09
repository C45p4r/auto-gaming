from __future__ import annotations

import time

from app.actions.executor import execute
from app.actions.types import TapAction
from app.games.epic7.presets import DEFAULT_PRESET
from app.services.capture import capture_frame
from app.state.encoder import encode_state


def navigate_to_adventure() -> None:
    # home -> battle -> adventure
    x, y = DEFAULT_PRESET.anchors["home_daily"]
    execute(TapAction(x=x, y=y))
    time.sleep(1.0)
    x, y = DEFAULT_PRESET.anchors["battle"]
    execute(TapAction(x=x, y=y))
    time.sleep(1.0)
    x, y = DEFAULT_PRESET.anchors["battle_event"]
    execute(TapAction(x=x, y=y))
    time.sleep(1.0)


def start_stage_run() -> None:
    x, y = DEFAULT_PRESET.anchors["battle_start"]
    execute(TapAction(x=x, y=y))


def run_daily_missions(max_steps: int = 10) -> None:
    steps = 0
    navigate_to_adventure()
    while steps < max_steps:
        img = capture_frame()
        _ = encode_state(img)
        # For MVP, just attempt to start stage repeatedly
        start_stage_run()
        time.sleep(2.0)
        steps += 1
