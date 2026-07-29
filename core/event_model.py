"""
Event model for Macro Recorder Pro.
Defines MouseEvent, KeyboardEvent, and SystemEvent dataclasses
used throughout the application.
"""

from dataclasses import dataclass
from typing import Literal, Optional


@dataclass
class MouseEvent:
    """
    A single captured mouse event.

    Fields:
        type:      The kind of event — "move", "click", or "scroll"
        x:         Horizontal screen coordinate (pixels)
        y:         Vertical screen coordinate (pixels)
        timestamp: Seconds elapsed since recording started (relative, not absolute)
        button:    Mouse button name for click events — "left", "right", "middle", "x1", "x2"
                   None for move and scroll events.
        pressed:   True when button is pressed down, False when released.
                   None for move and scroll events.
        dx:        Horizontal scroll delta (positive = right). Default 0.
        dy:        Vertical scroll delta (positive = up). Default 0.
    """

    type: Literal["move", "click", "scroll"]
    x: int
    y: int
    timestamp: float

    # Click fields
    button: Optional[str] = None
    pressed: Optional[bool] = None

    # Scroll fields
    dx: int = 0
    dy: int = 0

    def to_dict(self) -> dict:
        """Convert to a plain dict for JSON serialization."""
        return {
            "type": self.type,
            "x": self.x,
            "y": self.y,
            "timestamp": round(self.timestamp, 4),
            "button": self.button,
            "pressed": self.pressed,
            "dx": self.dx,
            "dy": self.dy,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "MouseEvent":
        """Reconstruct a MouseEvent from a dict."""
        return cls(**data)


@dataclass
class KeyboardEvent:
    """
    A single captured keyboard event.

    Fields:
        type:      "key_press" or "key_release"
        key:       String representation of the key (e.g. "a", "Key.shift", "Key.enter")
        timestamp: Seconds elapsed since recording started (relative)
    """

    type: Literal["key_press", "key_release"]
    key: str
    timestamp: float

    def to_dict(self) -> dict:
        """Convert to a plain dict for JSON serialization."""
        return {
            "type": self.type,
            "key": self.key,
            "timestamp": round(self.timestamp, 4),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "KeyboardEvent":
        """Reconstruct a KeyboardEvent from a dict."""
        return cls(**data)


# System / advanced event types
_SYSTEM_TYPES = frozenset({
    "run_app", "wait_seconds", "window_focus",
    "save_variable", "find_image", "key_combo",
    "if_condition", "else", "end_if", 
    "loop_start", "loop_end", "try_catch",
    "clipboard_copy", "clipboard_paste", "screenshot",
    "open_url", "http_request", "find_text_on_screen"
})


@dataclass
class SystemEvent:
    """
    An advanced action that is manually inserted (not captured by listeners).

    Fields:
        type:           One of the _SYSTEM_TYPES literals
        action:         Descriptive action‑type string
        value:          Main payload (app path, wait duration, text, etc.)
        variable_name:  For save_variable — the variable key / output path
        comment:        Optional user comment
        timestamp:      Seconds offset (relative to recording start)
    """

    type: str   # one of _SYSTEM_TYPES
    action: str
    value: str
    variable_name: str = ""
    comment: str = ""
    timestamp: float = 0.0

    def to_dict(self) -> dict:
        return {
            "type": self.type,
            "action": self.action,
            "value": self.value,
            "variable_name": self.variable_name,
            "comment": self.comment,
            "timestamp": round(self.timestamp, 4),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SystemEvent":
        return cls(
            type=data["type"],
            action=data.get("action", data["type"]),
            value=data.get("value", ""),
            variable_name=data.get("variable_name", ""),
            comment=data.get("comment", ""),
            timestamp=data.get("timestamp", 0.0),
        )


def event_from_dict(data: dict):
    """
    Route a dict to the correct event class based on its 'type' field.
    Returns a MouseEvent, KeyboardEvent, or SystemEvent.
    """
    event_type = data.get("type", "")
    if event_type in ("key_press", "key_release"):
        return KeyboardEvent.from_dict(data)
    if event_type in _SYSTEM_TYPES:
        return SystemEvent.from_dict(data)
    return MouseEvent.from_dict(data)


if __name__ == "__main__":
    # Quick round-trip test
    move = MouseEvent("move", 100, 200, 0.12345678)
    click = MouseEvent("click", 300, 400, 1.5, button="left", pressed=True)
    scroll = MouseEvent("scroll", 500, 600, 2.9999, dx=0, dy=-3)

    for label, event in [("move", move), ("click", click), ("scroll", scroll)]:
        d = event.to_dict()
        print(f"{label}: {d}")
        rebuilt = MouseEvent.from_dict(d)
        assert rebuilt.type == event.type, f"Round-trip failed for {label}"
        assert rebuilt.x == event.x
        assert rebuilt.y == event.y
        assert rebuilt.to_dict() == d, f"Dict round-trip mismatch for {label}"

    # KeyboardEvent round-trip test
    kp = KeyboardEvent("key_press", "a", 3.1234)
    kr = KeyboardEvent("key_release", "Key.shift", 3.5678)

    for label, event in [("key_press", kp), ("key_release", kr)]:
        d = event.to_dict()
        print(f"{label}: {d}")
        rebuilt = KeyboardEvent.from_dict(d)
        assert rebuilt.type == event.type
        assert rebuilt.key == event.key
        assert rebuilt.to_dict() == d, f"Dict round-trip mismatch for {label}"

    # SystemEvent round-trip test
    se = SystemEvent("run_app", "run_app", "notepad.exe", comment="open notepad")
    sd = se.to_dict()
    print(f"system: {sd}")
    se2 = SystemEvent.from_dict(sd)
    assert se2.type == se.type
    assert se2.value == se.value
    assert se2.to_dict() == sd

    # event_from_dict routing test
    assert isinstance(event_from_dict(move.to_dict()), MouseEvent)
    assert isinstance(event_from_dict(kp.to_dict()), KeyboardEvent)
    assert isinstance(event_from_dict(se.to_dict()), SystemEvent)
    print("event_from_dict routing OK")

    print("event_model.py OK")
