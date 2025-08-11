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

    def replace_from_jsonl(self, jsonl: str) -> int:
        import json

        steps: list[Step] = []
        for line in jsonl.splitlines():
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            steps.append(
                Step(
                    ts=str(obj.get("ts", "")),
                    action=str(obj.get("action", "")),
                    reason=str(obj.get("reason", "")),
                    image_path=obj.get("image_path"),
                )
            )
        self._steps = steps[-self._cap :]
        return len(self._steps)

    def to_jsonl(self) -> str:
        import json

        lines = []
        for s in self._steps:
            lines.append(
                json.dumps(
                    {
                        "ts": s.ts,
                        "action": s.action,
                        "reason": s.reason,
                        "image_path": s.image_path,
                    },
                    ensure_ascii=False,
                )
            )
        return "\n".join(lines)


session = SessionLog()
