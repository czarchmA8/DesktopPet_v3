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
    """Event of one mouse button."""
    state: InputState
    x: int
    """Cursor x in screen coordinates (follows the cursor while the button is held)."""
    y: int
    """Cursor y in screen coordinates (follows the cursor while the button is held)."""
    pressed_at: float
    """Time of the press."""
    released_at: float | None = None
    """Time of the release, None until the button is released."""
    hit_id: str | None = None
    """`hit_id` of the shape under the cursor at the press or release (kept while the button is held), or None."""

@dataclass
class MouseScroll:
    """Mouse wheel scroll."""
    x: int = 0
    """Horizontal scroll."""
    y: int = 0
    """Vertical scroll."""
    hit_id: str | None = None
    """`hit_id` of the shape under the cursor, or None."""
