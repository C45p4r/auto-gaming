import asyncio

from app.agents.orchestrator import orchestrate
from app.state.encoder import GameState


def test_orchestrate_returns_candidate() -> None:
    state = GameState(timestamp_utc="t", stamina_current=50, stamina_cap=100, ocr_text="", ocr_lines=[], ocr_tokens=[])

    async def run() -> None:
        cand = await orchestrate(state)
        assert isinstance(cand, tuple)
        assert len(cand) == 3

    asyncio.run(run())
