"""
System tray icon with state indicator and right-click menu.

Uses pystray with PIL-generated icons — no external image files needed.
Runs on a daemon thread so tkinter mainloop() can own the main thread.

NOTE (Windows 11): The tray icon may be hidden in the overflow area.
Click the ^ arrow in the taskbar, find the icon, and drag it to the
visible area for quick access.
"""

import os
import threading

# Force win32 backend on Windows (must be set BEFORE importing pystray)
os.environ.setdefault("PYSTRAY_BACKEND", "win32")

from PIL import Image, ImageDraw
import pystray
from pystray import MenuItem as item


def _make_icon(color: str) -> Image.Image:
    """Generate a simple colored circle icon (no external file needed)."""
    try:
        img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.ellipse([4, 4, 60, 60], fill=color, outline="white", width=3)
        return img
    except Exception as e:
        print(f"[Tray] Icon creation failed: {e}")
        return Image.new("RGBA", (64, 64), color)


ICON_COLORS = {
    "idle":      "#4A90D9",   # Blue
    "recording": "#E74C3C",   # Red
    "playing":   "#2ECC71",   # Green
}


class TrayIcon:
    """
    System tray icon with status indicator and right-click menu.

    States:
    - idle:      Blue  — ready to record or replay
    - recording: Red   — currently capturing mouse events
    - playing:   Green — currently replaying a macro
    """

    def __init__(self, app):
        self.app = app
        self._icon: pystray.Icon | None = None
        self._thread: threading.Thread | None = None
        self._state = "idle"
        self._started = threading.Event()

    def start(self):
        """Launch the tray icon in a daemon thread."""
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        # Wait briefly for the icon to initialise (up to 3 s)
        self._started.wait(timeout=3.0)

    def stop(self):
        """Shut down the tray icon cleanly."""
        if self._icon:
            try:
                self._icon.stop()
            except Exception:
                pass

    def set_state(self, state: str):
        """Update icon color to reflect app state (thread-safe)."""
        if state not in ICON_COLORS:
            return
        self._state = state
        if self._icon and self._icon.visible:
            try:
                self._icon.icon = _make_icon(ICON_COLORS[state])
                self._icon.title = f"Macro Recorder Pro — {state.capitalize()}"
            except Exception as e:
                print(f"[Tray] set_state failed: {e}")

    def _build_menu(self):
        return pystray.Menu(
            item("Macro Recorder Pro", lambda icon, item: None, enabled=False),
            pystray.Menu.SEPARATOR,
            item("▶  Start Recording (F8)", lambda icon, item: self.app.start_recording()),
            item("⏹  Stop & Save (F9)",     lambda icon, item: self.app.stop_recording()),
            pystray.Menu.SEPARATOR,
            item("⏯  Replay (F10)",         lambda icon, item: self.app.replay()),
            item("⛔  Abort (F11)",          lambda icon, item: self.app.abort()),
            pystray.Menu.SEPARATOR,
            item("📋  Open Editor",          lambda icon, item: self._open_editor()),
            pystray.Menu.SEPARATOR,
            item("❌  Quit",                 lambda icon, item: self._quit()),
        )

    def _open_editor(self):
        """Show/raise the main window (or fall back to legacy editor)."""
        if hasattr(self.app, 'window') and self.app.window:
            try:
                self.app.window.after(0, self._raise_window)
                return
            except Exception:
                pass
        # Fallback: launch old editor in a thread
        threading.Thread(target=self._launch_editor, daemon=True).start()

    def _raise_window(self):
        """Bring the main window to front."""
        w = self.app.window
        w.deiconify()
        w.lift()
        w.focus_force()

    def _launch_editor(self):
        """Fallback: launch legacy editor. Uses after() on main thread if available."""
        try:
            if hasattr(self.app, 'window') and self.app.window:
                # Schedule on main tkinter thread to avoid thread-safety issues
                self.app.window.after(0, self._launch_editor_on_main_thread)
                return
        except Exception:
            pass
        # Last resort — direct launch (only when no main window exists)
        from ui.editor import MacroEditor
        store = getattr(self.app, 'store', None)
        if store:
            editor = MacroEditor(store)
            editor.run()

    def _launch_editor_on_main_thread(self):
        from ui.editor import MacroEditor
        store = getattr(self.app, 'store', None)
        if store:
            editor = MacroEditor(store)
            # Use Toplevel instead of Tk() to avoid multiple Tk instances
            editor.run_as_toplevel(self.app.window)

    def _quit(self):
        self.app.quit()
        if self._icon:
            try:
                self._icon.stop()
            except Exception:
                pass

    def _run(self):
        self._icon = pystray.Icon(
            name="macro_recorder_pro",
            icon=_make_icon(ICON_COLORS["idle"]),
            title="Macro Recorder Pro — Idle",
            menu=self._build_menu(),
        )
        # Signal that setup() has been called
        self._icon.run(setup=lambda icon: self._on_setup(icon))

    def _on_setup(self, icon):
        """Called by pystray once the icon is ready."""
        icon.visible = True
        self._started.set()
        print("[Tray] Icon started successfully")
