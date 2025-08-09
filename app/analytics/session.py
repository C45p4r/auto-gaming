from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Step:
    ts: str
    action: str
    reason: str
    image_path: str | None


class SessionLog:
    def __init__(self) -> None:
        self._steps: list[Step] = []
        self._cap = 2000

    def add(self, step: Step) -> None:
        self._steps.append(step)
        if len(self._steps) > self._cap:
            del self._steps[0 : len(self._steps) - self._cap]

    def all(self) -> list[Step]:
        return self._steps


session = SessionLog()
