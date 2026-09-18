from dataclasses import dataclass
from enum import StrEnum, Enum, auto

class InputState(Enum):
    pressed = auto()
    holding = auto()
    released = auto()

class MouseButtonName(StrEnum):
    left = "LeftButton"
    middle = "MiddleButton"
    right = "RightButton"
    forward = "ForwardButton"
    back = "BackButton"

@dataclass
class MouseButtonEvent:
    state: InputState
    x: int
    y: int
    pressed_at: float
    released_at: float | None = None
    hit_id: str | None = None

@dataclass
class MouseScroll:
    x: int = 0
    y: int = 0
    hit_id: str | None = None
