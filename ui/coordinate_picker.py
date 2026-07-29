"""
Screen Coordinate Picker — fullscreen overlay with crosshair,
live coordinate tooltip, and magnified zoom view.

Usage:
    from ui.coordinate_picker import CoordinatePicker
    result = CoordinatePicker.pick(parent_window)
    # result is (x, y) or None if cancelled
"""

import tkinter as tk
import sys
from pathlib import Path
from typing import Optional

_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from ui.theme import (
    BG_PRIMARY, BG_SECONDARY, ACCENT, TEXT_COLOR, TEXT_DIM,
    FONT_MAIN, FONT_SMALL, FONT_BOLD, FONT_HEADER,
)

# Try to import win32 for accurate cursor position
try:
    import ctypes
    _user32 = ctypes.windll.user32

    class _POINT(ctypes.Structure):
        _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

    def _get_cursor_pos() -> tuple[int, int]:
        pt = _POINT()
        _user32.GetCursorPos(ctypes.byref(pt))
        return pt.x, pt.y

    def _get_dc():
        return _user32.GetDC(0)

    def _release_dc(hdc):
        _user32.ReleaseDC(0, hdc)

    _gdi32 = ctypes.windll.gdi32

    def _get_pixel(hdc, x, y) -> tuple[int, int, int]:
        colour = _gdi32.GetPixel(hdc, x, y)
        if colour == -1:
            return (0, 0, 0)
        r = colour & 0xFF
        g = (colour >> 8) & 0xFF
        b = (colour >> 16) & 0xFF
        return (r, g, b)

    _HAS_WIN32 = True
except Exception:
    _HAS_WIN32 = False

    def _get_cursor_pos():
        return (0, 0)


# ───────────────────────────────────────────────────────────────
# Magnifier settings
# ───────────────────────────────────────────────────────────────
ZOOM_FACTOR = 5           # 5× magnification
SAMPLE_RADIUS = 10        # Capture 21×21 pixel area (radius 10)
MAG_SIZE = (2 * SAMPLE_RADIUS + 1) * ZOOM_FACTOR  # 105 px rendered


class _PickerOverlay(tk.Toplevel):
    """Fullscreen transparent overlay for picking screen coordinates."""

    def __init__(self, parent: tk.Misc):
        super().__init__(parent)

        self.result: Optional[tuple[int, int]] = None

        # ── Window setup ─────────────────────────────────────
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.attributes("-alpha", 0.4)
        self.configure(bg="black", cursor="crosshair")

        # Cover the full virtual screen (all monitors)
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        self.geometry(f"{sw}x{sh}+0+0")

        # ── Canvas for drawing ───────────────────────────────
        self._canvas = tk.Canvas(
            self, width=sw, height=sh,
            bg="black", highlightthickness=0, cursor="crosshair",
        )
        self._canvas.pack(fill="both", expand=True)

        # Instructions label
        self._canvas.create_text(
            sw // 2, 40,
            text="Click to select coordinates  —  ESC to cancel",
            font=FONT_HEADER, fill="white", tags="static",
        )

        # Coordinate tooltip (repositioned each frame)
        self._coord_text = self._canvas.create_text(
            0, 0, text="", font=FONT_BOLD, fill=ACCENT, anchor="nw",
            tags="tooltip",
        )

        # Crosshair lines
        self._hline = self._canvas.create_line(0, 0, 0, 0, fill=ACCENT, width=1, dash=(4, 4))
        self._vline = self._canvas.create_line(0, 0, 0, 0, fill=ACCENT, width=1, dash=(4, 4))

        # Magnifier background rectangle
        self._mag_bg = self._canvas.create_rectangle(
            0, 0, MAG_SIZE + 4, MAG_SIZE + 4,
            fill=BG_SECONDARY, outline=ACCENT, width=2,
        )
        # Magnifier cells will be drawn as rectangles
        self._mag_cells: list[int] = []

        # ── Bindings ─────────────────────────────────────────
        self._canvas.bind("<Button-1>", self._on_click)
        self.bind("<Escape>", self._on_cancel)
        self.focus_force()

        # ── Start tracking loop ──────────────────────────────
        self._tracking = True
        self._update_loop()

    # ──────────────────────────────────────────────────────────
    def _update_loop(self):
        if not self._tracking:
            return

        cx, cy = _get_cursor_pos()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()

        # Update crosshair
        self._canvas.coords(self._hline, 0, cy, sw, cy)
        self._canvas.coords(self._vline, cx, 0, cx, sh)

        # Update tooltip — offset so it doesn't overlap cursor
        tx = cx + 20
        ty = cy - 30
        if tx + 120 > sw:
            tx = cx - 140
        if ty < 10:
            ty = cy + 25
        self._canvas.coords(self._coord_text, tx, ty)
        self._canvas.itemconfig(self._coord_text, text=f"X: {cx}  Y: {cy}")

        # Update magnifier position (bottom-right corner, but flip if near edge)
        mag_x = cx + 30
        mag_y = cy + 30
        if mag_x + MAG_SIZE + 10 > sw:
            mag_x = cx - MAG_SIZE - 30
        if mag_y + MAG_SIZE + 10 > sh:
            mag_y = cy - MAG_SIZE - 30

        self._canvas.coords(
            self._mag_bg,
            mag_x - 2, mag_y - 2,
            mag_x + MAG_SIZE + 2, mag_y + MAG_SIZE + 2,
        )

        # Draw magnified pixels (if win32 available)
        # Clear old cells
        for cid in self._mag_cells:
            self._canvas.delete(cid)
        self._mag_cells.clear()

        if _HAS_WIN32:
            hdc = _get_dc()
            try:
                for gy in range(-SAMPLE_RADIUS, SAMPLE_RADIUS + 1, 2):
                    for gx in range(-SAMPLE_RADIUS, SAMPLE_RADIUS + 1, 2):
                        px, py = cx + gx, cy + gy
                        r, g, b = _get_pixel(hdc, px, py)
                        colour = f"#{r:02x}{g:02x}{b:02x}"
                        rx = mag_x + (gx + SAMPLE_RADIUS) * ZOOM_FACTOR
                        ry = mag_y + (gy + SAMPLE_RADIUS) * ZOOM_FACTOR
                        cid = self._canvas.create_rectangle(
                            rx, ry, rx + ZOOM_FACTOR * 2, ry + ZOOM_FACTOR * 2,
                            fill=colour, outline="",
                        )
                        self._mag_cells.append(cid)
            finally:
                _release_dc(hdc)

        # Schedule next update (~30 fps)
        self.after(33, self._update_loop)

    # ──────────────────────────────────────────────────────────
    def _on_click(self, event):
        cx, cy = _get_cursor_pos()
        self.result = (cx, cy)
        self._tracking = False
        self.destroy()

    def _on_cancel(self, _event=None):
        self.result = None
        self._tracking = False
        self.destroy()


class CoordinatePicker:
    """Screen coordinate picker with crosshair + magnifier overlay."""

    @staticmethod
    def pick(parent_window: tk.Misc) -> Optional[tuple[int, int]]:
        """
        Show the picker overlay. Returns (x, y) or None if cancelled.
        Hides the parent window while picking.
        """
        # Hide parent
        was_visible = parent_window.winfo_viewable()
        if was_visible:
            parent_window.withdraw()
            parent_window.update()

        overlay = _PickerOverlay(parent_window)
        overlay.wait_window()

        # Restore parent
        if was_visible:
            parent_window.deiconify()

        return overlay.result


# ───────────────────────────────────────────────────────────────
# Standalone test
# ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    root = tk.Tk()
    root.title("Coordinate Picker Test")
    root.geometry("300x100")
    root.configure(bg=BG_PRIMARY)

    result_var = tk.StringVar(value="Click the button to pick coordinates")
    tk.Label(root, textvariable=result_var, bg=BG_PRIMARY, fg=TEXT_COLOR,
             font=FONT_MAIN).pack(expand=True)

    def do_pick():
        coords = CoordinatePicker.pick(root)
        if coords:
            result_var.set(f"Selected: X={coords[0]}, Y={coords[1]}")
        else:
            result_var.set("Cancelled")

    tk.Button(root, text="Pick Coordinates", command=do_pick,
              bg=ACCENT, fg=TEXT_COLOR, font=FONT_BOLD,
              relief="flat").pack(pady=10)

    root.mainloop()
