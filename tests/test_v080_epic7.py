from app.games.epic7.presets import DEFAULT_PRESET, Epic7Preset


def test_epic7_preset_has_anchors() -> None:
    assert isinstance(DEFAULT_PRESET, Epic7Preset)
    assert "battle_start" in DEFAULT_PRESET.anchors
