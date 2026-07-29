"""
Conditional triggers for macro playback.

Triggers check a condition before allowing macro execution.
Includes: time-based, pixel color, window title, and key-held triggers.
"""

import time
import threading
from datetime import datetime


class Trigger:
    """Base class for all triggers."""

    def is_ready(self) -> bool:
        raise NotImplementedError


class TimeTrigger(Trigger):
    """Run macro at a specific time of day."""

    def __init__(self, hour: int, minute: int):
        self.hour = hour
        self.minute = minute

    def is_ready(self) -> bool:
        now = datetime.now()
        return now.hour == self.hour and now.minute == self.minute

    def wait_until_ready(self):
        """Block until the trigger time arrives."""
        print(f"[TimeTrigger] Waiting until {self.hour:02d}:{self.minute:02d}...")
        while not self.is_ready():
            time.sleep(10)  # Check every 10 seconds
        print("[TimeTrigger] Triggered!")


class PixelColorTrigger(Trigger):
    """Run macro only if a specific screen pixel is a certain color."""

    def __init__(self, x: int, y: int, expected_color: tuple[int, int, int], tolerance: int = 10):
        self.x = x
        self.y = y
        self.expected_color = expected_color  # (R, G, B)
        self.tolerance = tolerance

    def _get_pixel_color(self) -> tuple[int, int, int]:
        """Read a single pixel color from the screen using Win32 GDI."""
        import ctypes
        hdc = ctypes.windll.user32.GetDC(0)
        color = ctypes.windll.gdi32.GetPixel(hdc, self.x, self.y)
        ctypes.windll.user32.ReleaseDC(0, hdc)
        r = color & 0xFF
        g = (color >> 8) & 0xFF
        b = (color >> 16) & 0xFF
        return (r, g, b)

    def is_ready(self) -> bool:
        actual = self._get_pixel_color()
        for a, e in zip(actual, self.expected_color):
            if abs(a - e) > self.tolerance:
                return False
        return True


class WindowTitleTrigger(Trigger):
    """Run macro only if a specific window title is currently active."""

    def __init__(self, title_contains: str, case_sensitive: bool = False):
        self.title_contains = title_contains
        self.case_sensitive = case_sensitive

    def _get_active_title(self) -> str:
        """Get the title of the currently focused window."""
        import win32gui
        return win32gui.GetWindowText(win32gui.GetForegroundWindow())

    def is_ready(self) -> bool:
        title = self._get_active_title()
        if self.case_sensitive:
            return self.title_contains in title
        return self.title_contains.lower() in title.lower()


class KeyHeldTrigger(Trigger):
    """Run macro only while a key is being held down."""

    def __init__(self, key: str):
        self.key = key

    def is_ready(self) -> bool:
        import keyboard
        return keyboard.is_pressed(self.key)


class FileChangeTrigger(Trigger):
    """Run macro when a file is modified."""

    def __init__(self, file_path: str):
        import os
        self.file_path = file_path
        self.last_mtime = os.path.getmtime(file_path) if os.path.exists(file_path) else 0

    def is_ready(self) -> bool:
        import os
        if not os.path.exists(self.file_path):
            return False
        current_mtime = os.path.getmtime(self.file_path)
        if current_mtime > self.last_mtime:
            self.last_mtime = current_mtime
            return True
        return False


class ClipboardTrigger(Trigger):
    """Run macro when the clipboard content changes."""

    def __init__(self):
        import pyperclip
        self.last_content = pyperclip.paste()

    def is_ready(self) -> bool:
        import pyperclip
        current_content = pyperclip.paste()
        if current_content != self.last_content:
            self.last_content = current_content
            return True
        return False


class ProcessTrigger(Trigger):
    """Run macro when a specific process launches or exits."""

    def __init__(self, process_name: str, on_launch: bool = True):
        self.process_name = process_name.lower()
        self.on_launch = on_launch
        self.was_running = self._is_running()

    def _is_running(self) -> bool:
        import psutil
        for proc in psutil.process_iter(['name']):
            try:
                if proc.info['name'] and self.process_name in proc.info['name'].lower():
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        return False

    def is_ready(self) -> bool:
        is_running = self._is_running()
        triggered = False
        if self.on_launch and not self.was_running and is_running:
            triggered = True
        elif not self.on_launch and self.was_running and not is_running:
            triggered = True
        
        self.was_running = is_running
        return triggered


class ConditionalRunner:
    """
    Runs a macro only when a trigger condition is met.
    Polls the trigger on an interval.
    """

    def __init__(self, player, trigger: Trigger, poll_interval: float = 0.5):
        self.player = player
        self.trigger = trigger
        self.poll_interval = poll_interval
        self._active = False

    def start_watching(self, events, loops: int = 1):
        """Start watching for trigger condition."""
        self._active = True

        def watcher():
            while self._active:
                if self.trigger.is_ready():
                    print("[ConditionalRunner] Trigger fired — starting replay")
                    self.player.replay(events, loops=loops)
                    self.player.wait_until_done()
                time.sleep(self.poll_interval)

        threading.Thread(target=watcher, daemon=True).start()

    def stop(self):
        """Stop watching and abort any active replay."""
        self._active = False
        self.player.abort()
