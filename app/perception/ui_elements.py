from dataclasses import dataclass


@dataclass(frozen=True)
class UiButton:
    label: str | None
    x: int
    y: int
    w: int
    h: int


@dataclass(frozen=True)
class ResourceCounter:
    name: str
    value: int
