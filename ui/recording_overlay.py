"""
Recording Status Overlay — floating red badge showing recording state.
Always-on-top, no title bar, positioned top-right of screen.
"""

import tkinter as tk
import time

import sys
from pathlib import Path

_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from ui.theme import ACCENT, TEXT_COLOR, FONT_BOLD, FONT_SMALL


class RecordingOverlay(tk.Toplevel):
    """
    Floating red badge shown during recording.
    Displays:  ⏺ REC 0:00:04  47 events
    Click to stop recording.
    """

    def __init__(self, parent: tk.Misc, on_stop=None):
        super().__init__(parent)
        self.overrideredirect(True)      # no title bar
        self.attributes("-topmost", True)
        self.configure(bg=ACCENT)

        self._on_stop = on_stop
        self._start_time = time.perf_counter()
        self._event_count = 0
        self._running = True

        # ── Layout ────────────────────────────────────────────
        frame = tk.Frame(self, bg=ACCENT, padx=14, pady=6)
        frame.pack()

        self._label = tk.Label(
            frame,
            text="⏺ REC  0:00:00   0 events",
            font=FONT_BOLD, bg=ACCENT, fg=TEXT_COLOR,
        )
        self._label.pack(side="left")

        tk.Label(frame, text="  │  ", font=FONT_SMALL,
                 bg=ACCENT, fg=TEXT_COLOR).pack(side="left")

        stop_btn = tk.Label(
            frame, text="⏹ Stop", font=FONT_BOLD,
            bg=ACCENT, fg=TEXT_COLOR, cursor="hand2",
        )
        stop_btn.pack(side="left")
        stop_btn.bind("<Button-1>", self._stop_click)

        # Make entire overlay draggable
        self._drag_data = {"x": 0, "y": 0}
        frame.bind("<Button-1>", self._start_drag)
        frame.bind("<B1-Motion>", self._do_drag)
        self._label.bind("<Button-1>", self._start_drag)
        self._label.bind("<B1-Motion>", self._do_drag)

        # Position: top-right of screen
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        self.geometry(f"+{sw - self.winfo_reqwidth() - 20}+20")

        # Start update loop
        self._update()

    def set_event_count(self, n: int):
        self._event_count = n

    def _update(self):
        if not self._running:
            return
        elapsed = time.perf_counter() - self._start_time
        h, rem = divmod(int(elapsed), 3600)
        m, s = divmod(rem, 60)
        self._label.config(
            text=f"⏺ REC  {h}:{m:02d}:{s:02d}   {self._event_count} events"
        )
        self.after(1000, self._update)

    def stop(self):
        """Close the overlay."""
        self._running = False
        try:
            self.destroy()
        except tk.TclError:
            pass

    def _stop_click(self, _e):
        if self._on_stop:
            self._on_stop()
        self.stop()

    def _start_drag(self, e):
        self._drag_data["x"] = e.x_root - self.winfo_x()
        self._drag_data["y"] = e.y_root - self.winfo_y()

    def _do_drag(self, e):
        x = e.x_root - self._drag_data["x"]
        y = e.y_root - self._drag_data["y"]
        self.geometry(f"+{x}+{y}")
