"""
Mouse event recorder with smart throttling.

Captures mouse movements, clicks, and scrolls via pynput.
Move events are throttled to reduce volume without losing accuracy.
"""

import time
import math
import threading
from pynput import mouse, keyboard
from core.event_model import MouseEvent, KeyboardEvent, SystemEvent


class Recorder:
    """
    Records mouse events with smart throttling.

    Throttle rules:
    - Move events: only recorded if mouse moved >5px OR >50ms passed
    - Click events: always recorded (never throttled)
    - Scroll events: always recorded
    """

    def __init__(self):
        import config
        self.MOVE_DISTANCE_THRESHOLD = getattr(config, 'MOVE_DISTANCE_THRESHOLD', 5)
        self.MOVE_TIME_THRESHOLD = getattr(config, 'MOVE_TIME_THRESHOLD', 0.05)

        self.events: list[MouseEvent | KeyboardEvent] = []
        self.is_recording: bool = False

        self._start_time: float = 0.0
        self._listener: mouse.Listener | None = None
        self._kb_listener: keyboard.Listener | None = None
        self._lock = threading.Lock()

        # Throttle tracking
        self._last_move_x: int = 0
        self._last_move_y: int = 0
        self._last_move_time: float = 0.0

    # ── Public API ──────────────────────────────────────────

    def start(self):
        """Start recording. Clears any previous recording."""
        if self.is_recording:
            return

        with self._lock:
            self.events.clear()
            self.is_recording = True
            self._start_time = time.perf_counter()
            self._last_move_time = 0.0

        self._listener = mouse.Listener(
            on_move=self._on_move,
            on_click=self._on_click,
            on_scroll=self._on_scroll,
        )
        self._listener.start()

        self._kb_listener = keyboard.Listener(
            on_press=self._on_key_press,
            on_release=self._on_key_release,
        )
        self._kb_listener.start()

        print("[Recorder] Started")

    def stop(self) -> list[MouseEvent | KeyboardEvent]:
        """Stop recording. Returns the captured event list."""
        if not self.is_recording:
            return self.events

        self.is_recording = False

        if self._listener:
            self._listener.stop()
            self._listener = None

        if self._kb_listener:
            self._kb_listener.stop()
            self._kb_listener = None

        print(f"[Recorder] Stopped — {len(self.events)} events captured")
        return self.events

    def get_duration(self) -> float:
        """Returns duration of the recording in seconds."""
        if not self.events:
            return 0.0
        return self.events[-1].timestamp

    # ── Internal Handlers ────────────────────────────────────

    def _elapsed(self) -> float:
        """Returns seconds elapsed since recording started."""
        return time.perf_counter() - self._start_time

    def _on_move(self, x: int, y: int):
        if not self.is_recording:
            return

        now = self._elapsed()

        # Throttle: skip if too close in position AND too recent in time
        dist = math.hypot(x - self._last_move_x, y - self._last_move_y)
        time_since_last = now - self._last_move_time

        if dist < self.MOVE_DISTANCE_THRESHOLD and time_since_last < self.MOVE_TIME_THRESHOLD:
            return

        self._last_move_x = x
        self._last_move_y = y
        self._last_move_time = now

        with self._lock:
            self.events.append(MouseEvent("move", x, y, now))

    def _on_click(self, x: int, y: int, button, pressed: bool):
        if not self.is_recording:
            return

        with self._lock:
            self.events.append(MouseEvent(
                type="click",
                x=x,
                y=y,
                timestamp=self._elapsed(),
                button=button.name,
                pressed=pressed,
            ))

    def _on_scroll(self, x: int, y: int, dx: int, dy: int):
        if not self.is_recording:
            return

        with self._lock:
            self.events.append(MouseEvent(
                type="scroll",
                x=x,
                y=y,
                timestamp=self._elapsed(),
                dx=dx,
                dy=dy,
            ))

    # ── Keyboard Handlers ────────────────────────────────────

    @staticmethod
    def _key_to_str(key) -> str:
        """
        Convert a pynput key object to a consistent string.
        - Character keys → e.g. "a", "1", "/"
        - Special keys   → e.g. "Key.shift", "Key.enter", "Key.ctrl_l"
        """
        if hasattr(key, 'char') and key.char is not None:
            return key.char
        return str(key)          # e.g. "Key.shift"

    def _on_key_press(self, key):
        if not self.is_recording:
            return

        with self._lock:
            self.events.append(KeyboardEvent(
                type="key_press",
                key=self._key_to_str(key),
                timestamp=self._elapsed(),
            ))

    def _on_key_release(self, key):
        if not self.is_recording:
            return

        with self._lock:
            self.events.append(KeyboardEvent(
                type="key_release",
                key=self._key_to_str(key),
                timestamp=self._elapsed(),
            ))

    # ── Manual Action Insertion ──────────────────────────────

    def insert_action(
        self,
        action_type: str,
        value: str,
        comment: str = "",
        variable_name: str = "",
    ) -> SystemEvent:
        """
        Manually add a SystemEvent (used by the UI "Add Action" dialog).
        The timestamp is set to the current elapsed time if recording,
        or appended after the last event otherwise.
        """
        if self.is_recording:
            ts = self._elapsed()
        elif self.events:
            ts = self.events[-1].timestamp + 0.01
        else:
            ts = 0.0

        event = SystemEvent(
            type=action_type,
            action=action_type,
            value=value,
            variable_name=variable_name,
            comment=comment,
            timestamp=ts,
        )
        with self._lock:
            self.events.append(event)
        print(f"[Recorder] Inserted {action_type}: {value}")
        return event
