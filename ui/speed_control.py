"""
Speed Control dialog — dark-themed slider with presets.
"""

import tkinter as tk
from typing import Optional, Callable

import sys
from pathlib import Path

_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from ui.theme import (
    BG_PRIMARY, BG_SECONDARY, ACCENT, ACCENT_HOVER,
    TEXT_COLOR, TEXT_DIM, BORDER_COLOR,
    FONT_MAIN, FONT_SMALL, FONT_BOLD, FONT_HEADER,
)


class SpeedControlDialog(tk.Toplevel):
    """Modal speed-control dialog with slider + preset buttons."""

    def __init__(self, parent: tk.Misc, current_speed: float = 1.0,
                 on_apply: Optional[Callable[[float], None]] = None):
        super().__init__(parent)
        self.title("Playback Speed")
        self.configure(bg=BG_PRIMARY)
        self.geometry("360x220")
        self.resizable(False, False)
        self.transient(parent)

        self._speed = tk.DoubleVar(value=current_speed)
        self._on_apply = on_apply

        self._build_ui()

        # Centre on parent
        self.update_idletasks()
        px = parent.winfo_rootx() + (parent.winfo_width() - self.winfo_width()) // 2
        py = parent.winfo_rooty() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{max(px, 0)}+{max(py, 0)}")

        self.bind("<Escape>", lambda e: self.destroy())

    def _build_ui(self):
        tk.Label(self, text="Playback Speed", font=FONT_HEADER,
                 bg=BG_PRIMARY, fg=TEXT_COLOR).pack(pady=(16, 4))

        # Live preview
        self._preview = tk.Label(self, text=self._fmt(self._speed.get()),
                                 font=("Segoe UI", 28, "bold"),
                                 bg=BG_PRIMARY, fg=ACCENT)
        self._preview.pack(pady=(0, 8))

        # Slider
        slider = tk.Scale(
            self, from_=0.1, to=5.0, resolution=0.1, orient="horizontal",
            variable=self._speed, command=self._on_slide,
            bg=BG_PRIMARY, fg=TEXT_COLOR, troughcolor=BG_SECONDARY,
            activebackground=ACCENT, highlightthickness=0,
            sliderlength=20, length=300, font=FONT_SMALL,
        )
        slider.pack(padx=20)

        # Preset buttons
        presets_fr = tk.Frame(self, bg=BG_PRIMARY)
        presets_fr.pack(pady=(10, 6))

        presets = [("0.5× Slow", 0.5), ("1.0× Normal", 1.0),
                   ("2.0× Fast", 2.0), ("Max Speed", 5.0)]
        for label, val in presets:
            tk.Button(
                presets_fr, text=label, font=FONT_SMALL,
                bg=BG_SECONDARY, fg=TEXT_COLOR,
                activebackground=ACCENT, activeforeground=TEXT_COLOR,
                relief="flat", bd=0, cursor="hand2",
                command=lambda v=val: self._set_preset(v),
            ).pack(side="left", padx=4, ipady=3, ipadx=6)

        # Apply / Close
        btn_fr = tk.Frame(self, bg=BG_PRIMARY)
        btn_fr.pack(pady=(4, 12))
        tk.Button(btn_fr, text="Apply", font=FONT_BOLD,
                  bg=ACCENT, fg=TEXT_COLOR, activebackground=ACCENT_HOVER,
                  activeforeground=TEXT_COLOR, relief="flat", bd=0,
                  cursor="hand2", width=10, command=self._apply).pack(
            side="left", padx=6, ipady=4)
        tk.Button(btn_fr, text="Close", font=FONT_MAIN,
                  bg=BG_SECONDARY, fg=TEXT_COLOR, activebackground=ACCENT,
                  activeforeground=TEXT_COLOR, relief="flat", bd=0,
                  cursor="hand2", width=10, command=self.destroy).pack(
            side="left", ipady=4)

    @staticmethod
    def _fmt(val: float) -> str:
        return f"{val:.1f}×"

    def _on_slide(self, _val):
        self._preview.config(text=self._fmt(self._speed.get()))

    def _set_preset(self, val: float):
        self._speed.set(val)
        self._preview.config(text=self._fmt(val))

    def _apply(self):
        if self._on_apply:
            self._on_apply(self._speed.get())
        self.destroy()


def open_speed_dialog(parent: tk.Misc, current_speed: float = 1.0,
                      on_apply=None):
    """Convenience launcher."""
    SpeedControlDialog(parent, current_speed, on_apply)
