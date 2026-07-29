"""
Global hotkey manager using the keyboard library.

Registers hotkeys that work system-wide — even when the app window is not focused.
"""

import keyboard
from typing import Callable


class HookManager:
    """
    Registers and manages global hotkeys.
    Hotkeys work system-wide — even when app is not focused.
    """

    def __init__(self):
        self._hotkeys: dict[str, Callable] = {}

    def register(self, hotkey: str, callback: Callable, description: str = ""):
        """Register a global hotkey. Overwrites existing binding."""
        # Remove existing binding if present
        if hotkey in self._hotkeys:
            try:
                keyboard.remove_hotkey(hotkey)
            except KeyError:
                pass

        keyboard.add_hotkey(hotkey, callback, suppress=False)
        self._hotkeys[hotkey] = callback

        label = description or hotkey
        print(f"[HookManager] Registered: {hotkey.upper():15} -> {label}")

    def unregister(self, hotkey: str):
        """Remove a hotkey binding."""
        if hotkey in self._hotkeys:
            try:
                keyboard.remove_hotkey(hotkey)
            except KeyError:
                pass
            del self._hotkeys[hotkey]

    def unregister_all(self):
        """Remove all registered hotkeys."""
        for hotkey in list(self._hotkeys.keys()):
            self.unregister(hotkey)

    def list_hotkeys(self) -> list[str]:
        """Returns list of registered hotkey strings."""
        return list(self._hotkeys.keys())

    def block_until_exit(self, exit_hotkey: str = "ctrl+shift+q"):
        """Block the main thread. Use at end of main.py."""
        print(f"\nPress {exit_hotkey.upper()} to quit.")
        keyboard.wait(exit_hotkey)
