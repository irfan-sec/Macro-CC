"""
Mouse event player with accurate timing and abort support.

Replays recorded macros using absolute timestamp math to prevent drift.
Runs in a background thread so hotkeys remain responsive.
"""

import time
import subprocess
import threading
from pynput.mouse import Controller as MouseController, Button
from pynput.keyboard import Controller as KeyboardController, Key
from core.event_model import MouseEvent, KeyboardEvent, SystemEvent
from core.variables import VariableStore
from core.condition_engine import ConditionEngine
from core.execution_log import ExecutionLog
from core.screen_utils import ScreenUtils


# Map string button names → pynput Button enum
BUTTON_MAP = {
    "left":   Button.left,
    "right":  Button.right,
    "middle": Button.middle,
    "x1":     Button.x1,
    "x2":     Button.x2,
}

# Keys to skip during replay (hotkeys used by the macro tool itself)
SKIP_KEYS = {"Key.f7", "Key.f8", "Key.f9", "Key.f10", "Key.f11"}


class Player:
    """
    Replays a list of MouseEvents with accurate relative timing.

    Key behaviors:
    - Uses absolute timestamp math (not cumulative sleep) to prevent drift
    - Runs replay in a background thread so hotkeys keep working
    - Supports speed_multiplier: 0.5 = 2x faster, 2.0 = 2x slower
    - abort_flag lets you stop mid-replay cleanly
    """

    def __init__(self):
        self.mouse = MouseController()
        self.keyboard = KeyboardController()
        self.speed_multiplier: float = 1.0
        self.is_playing: bool = False
        self.variables = VariableStore()
        self.condition_engine = ConditionEngine(self.variables)
        self.execution_log = None

        # Playback progress callbacks
        self._on_event_complete = None    # callback(event_index, total_events)
        self._on_progress = None          # callback(current_event, total, loop, total_loops)

        self._abort_flag = threading.Event()
        self._pause_flag = threading.Event()
        self._replay_thread: threading.Thread | None = None

    # ── Public API ───────────────────────────────────────────

    def replay(
        self,
        events: list,
        loops: int = 1,
        on_loop_complete=None,
        on_done=None,
        on_each_loop_done=None,
    ):
        """
        Start replaying events in a background thread.

        Args:
            events: The macro to replay
            loops: How many times to repeat (0 = infinite)
            on_loop_complete: Optional callback(loop_number) after each loop
            on_done: Optional callback() when all loops finish or aborted
            on_each_loop_done: Optional callback(loop_number) fired after
                               EVERY single loop completes (for proxy rotation)
        """
        if self.is_playing:
            print("[Player] Already playing — call abort() first")
            return

        self._abort_flag.clear()
        self._replay_thread = threading.Thread(
            target=self._replay_worker,
            args=(events, loops, on_loop_complete, on_done, on_each_loop_done),
            daemon=True,
        )
        self._replay_thread.start()

    def abort(self):
        """Stop playback at the next safe checkpoint."""
        self._abort_flag.set()
        self._pause_flag.clear() # Un-pause to allow abort to process
        print("[Player] Abort requested")

    def pause(self):
        """Pause playback."""
        self._pause_flag.set()
        print("[Player] Paused")

    def resume(self):
        """Resume playback."""
        self._pause_flag.clear()
        print("[Player] Resumed")

    def wait_until_done(self, timeout: float = None):
        """Block until replay finishes. Use in scripts/tests."""
        if self._replay_thread:
            self._replay_thread.join(timeout=timeout)

    # ── Internal Worker ──────────────────────────────────────

    def _replay_worker(self, events, loops, on_loop_complete, on_done, on_each_loop_done=None):
        self.is_playing = True
        loop_count = 0

        try:
            while True:
                if self._abort_flag.is_set():
                    break

                # loops=0 means infinite; otherwise check count
                if loops != 0 and loop_count >= loops:
                    break

                loop_count += 1
                print(f"[Player] Loop {loop_count}" + (f"/{loops}" if loops != 0 else " (∞)"))

                self._play_once(events, loop_count, loops)

                # Fire after EVERY single loop completion
                if on_each_loop_done:
                    on_each_loop_done(loop_count)

                if on_loop_complete:
                    on_loop_complete(loop_count)

            print(f"[Player] Done — completed {loop_count} loops")

        finally:
            self.is_playing = False
            if on_done:
                on_done()

    def _play_once(self, events: list[MouseEvent | KeyboardEvent | SystemEvent],
                   current_loop: int = 1, total_loops: int = 1):
        """Play through all events once with accurate timing and control flow."""
        if not events:
            return

        total = len(events)
        replay_start = time.perf_counter()
        
        # Initialize execution log
        self.execution_log = ExecutionLog(macro_name="Run")

        idx = 0
        while idx < total:
            if self._abort_flag.is_set():
                break
                
            # Handle pause
            while self._pause_flag.is_set() and not self._abort_flag.is_set():
                time.sleep(0.1)
                
            event = events[idx]

            # Skip hotkey events so replay doesn't trigger tool hotkeys
            if isinstance(event, KeyboardEvent) and event.key in SKIP_KEYS:
                idx += 1
                continue

            # Calculate when this event SHOULD happen
            target_time = replay_start + (event.timestamp / self.speed_multiplier)

            # Sleep until target time (accurate to ~1ms)
            self._precise_sleep_until(target_time)

            if self._abort_flag.is_set():
                break

            # Execute with error recovery and logging
            event_start = time.perf_counter()
            status = "SUCCESS"
            error_msg = None
            
            try:
                # For control flow events, we need to pass idx and events
                if isinstance(event, SystemEvent) and event.type in ("if_condition", "else", "loop_start", "try_catch"):
                    idx = self._execute_control_flow(event, idx, events)
                else:
                    self._execute_event(event)
            except Exception as e:
                status = "FAILED"
                error_msg = str(e)
                print(f"[Player] Action {idx} failed: {e}")
                
            duration = time.perf_counter() - event_start
            
            # Log it
            self.execution_log.add_entry(
                index=idx,
                action_type=event.type,
                details=getattr(event, 'value', getattr(event, 'key', 'move/click')),
                status=status,
                duration=duration,
                error=error_msg
            )

            # Fire progress callback
            if self._on_progress:
                try:
                    self._on_progress(idx + 1, total, current_loop, total_loops)
                except Exception:
                    pass
                    
            idx += 1
            
        # Save log at the end
        if self.execution_log:
            self.execution_log.save()

    def _execute_control_flow(self, event: SystemEvent, current_idx: int, events: list) -> int:
        """Handle branching logic like if/else. Returns the next index to execute."""
        if event.type == "if_condition":
            condition_met = self.condition_engine.evaluate(event.value)
            print(f"[Player] if_condition '{event.value}' -> {condition_met}")
            
            if not condition_met:
                # Skip forward until we hit 'else' or 'end_if'
                idx = current_idx + 1
                nesting = 0
                while idx < len(events):
                    e = events[idx]
                    if isinstance(e, SystemEvent):
                        if e.type == "if_condition":
                            nesting += 1
                        elif e.type == "end_if":
                            if nesting == 0:
                                return idx
                            nesting -= 1
                        elif e.type == "else" and nesting == 0:
                            return idx
                    idx += 1
                return idx
                
        elif event.type == "else":
            # If we hit an 'else' naturally (meaning the 'if' was true), skip to 'end_if'
            idx = current_idx + 1
            nesting = 0
            while idx < len(events):
                e = events[idx]
                if isinstance(e, SystemEvent):
                    if e.type == "if_condition":
                        nesting += 1
                    elif e.type == "end_if":
                        if nesting == 0:
                            return idx
                        nesting -= 1
                idx += 1
            return idx
            
        # For now, loops just pass through (relying on outer loop runner)
        return current_idx

    def _precise_sleep_until(self, target_time: float):
        """
        Sleep until target_time using a hybrid approach:
        - Long waits: time.sleep() to avoid busy-waiting
        - Short waits (<2ms): spin-wait for accuracy
        """
        while True:
            remaining = target_time - time.perf_counter()
            if remaining <= 0:
                break
            if remaining > 0.002:
                time.sleep(remaining * 0.9)  # Sleep 90% of remaining time
            # else: spin for final <2ms (high accuracy)

    def _execute_event(self, event: MouseEvent | KeyboardEvent | SystemEvent):
        """Dispatch a single event to the OS."""
        if event.type == "move":
            self.mouse.position = (event.x, event.y)

        elif event.type == "click":
            self.mouse.position = (event.x, event.y)
            btn = BUTTON_MAP.get(event.button, Button.left)
            if event.pressed:
                self.mouse.press(btn)
            else:
                self.mouse.release(btn)

        elif event.type == "scroll":
            self.mouse.position = (event.x, event.y)
            self.mouse.scroll(event.dx, event.dy)

        elif event.type in ("key_press", "key_release"):
            parsed = self._parse_key(event.key)
            if event.type == "key_press":
                self.keyboard.press(parsed)
            else:
                self.keyboard.release(parsed)

        elif isinstance(event, SystemEvent):
            self._execute_system_event(event)

    @staticmethod
    def _parse_key(key_str: str):
        """
        Convert a key string back to a pynput Key or character.
        - "Key.shift" → Key.shift
        - "a"         → "a"
        """
        if key_str.startswith("Key."):
            key_name = key_str[4:]      # strip "Key."
            try:
                return Key[key_name]
            except KeyError:
                return key_name         # fallback: send as string
        return key_str                  # single character

    # ── SystemEvent execution ────────────────────────────────

    def _execute_system_event(self, event: SystemEvent):
        """Handle advanced / manually‑inserted system actions."""
        t = event.type

        if t == "run_app":
            try:
                subprocess.Popen(event.value, shell=True)
                print(f"[Player] Launched: {event.value}")
            except Exception as exc:
                print(f"[Player] run_app error: {exc}")

        elif t == "wait_seconds":
            try:
                secs = float(event.value)
                time.sleep(secs)
            except ValueError:
                print(f"[Player] wait_seconds: invalid value '{event.value}'")

        elif t == "window_focus":
            try:
                import win32gui
                hwnd = win32gui.FindWindow(None, event.value)
                if hwnd:
                    win32gui.SetForegroundWindow(hwnd)
                    print(f"[Player] Focused window: {event.value}")
                else:
                    # Substring match fallback
                    def _cb(h, extra):
                        if event.value.lower() in win32gui.GetWindowText(h).lower():
                            extra.append(h)
                    found: list[int] = []
                    win32gui.EnumWindows(_cb, found)
                    if found:
                        win32gui.SetForegroundWindow(found[0])
                        print(f"[Player] Focused window (partial): {win32gui.GetWindowText(found[0])}")
                    else:
                        print(f"[Player] Window not found: {event.value}")
            except Exception as exc:
                print(f"[Player] window_focus error: {exc}")

        elif t == "key_combo":
            # Parse "ctrl+c" style strings — substitute variables first
            combo_str = self.variables.substitute(event.value) if hasattr(self, 'variables') else event.value
            parts = [p.strip().lower() for p in combo_str.split("+")]
            keys = [self._parse_combo_key(p) for p in parts]
            # Press all in order, then release in reverse
            for k in keys:
                self.keyboard.press(k)
            for k in reversed(keys):
                self.keyboard.release(k)
            print(f"[Player] Key combo: {event.value}")

        elif t == "save_variable":
            # Store variable; if variable_name is a .txt path, also write file
            if hasattr(self, 'variables'):
                self.variables.set(event.variable_name, event.value)
            if event.variable_name.endswith(".txt"):
                try:
                    with open(event.variable_name, "w", encoding="utf-8") as f:
                        f.write(event.value)
                    print(f"[Player] Saved variable to file: {event.variable_name}")
                except Exception as exc:
                    print(f"[Player] save_variable file error: {exc}")
            else:
                print(f"[Player] Variable '{event.variable_name}' = '{event.value}'")

        elif t == "find_image":
            img_path = self.variables.substitute(event.value) if hasattr(self, 'variables') else event.value
            coords = ScreenUtils.find_image_on_screen(img_path)
            if coords:
                x, y = coords
                # Default behavior: move mouse to the image
                self.mouse.position = (x, y)
                if event.variable_name and hasattr(self, 'variables'):
                    self.variables.set(event.variable_name, f"{x},{y}")
                print(f"[Player] Found image '{img_path}' at {x}, {y}")
            else:
                raise Exception(f"Image '{img_path}' not found on screen.")
                
        elif t == "find_text_on_screen":
            text = self.variables.substitute(event.value) if hasattr(self, 'variables') else event.value
            found = ScreenUtils.find_text_on_screen(text)
            if event.variable_name and hasattr(self, 'variables'):
                self.variables.set(event.variable_name, "true" if found else "false")
            
            if found:
                print(f"[Player] Found text '{text}' on screen.")
            else:
                raise Exception(f"Text '{text}' not found on screen.")
            
        elif t == "clipboard_copy":
            import pyperclip
            val = self.variables.substitute(event.value) if hasattr(self, 'variables') else event.value
            pyperclip.copy(val)
            print(f"[Player] Copied to clipboard: {val}")
            
        elif t == "open_url":
            import webbrowser
            url = self.variables.substitute(event.value) if hasattr(self, 'variables') else event.value
            webbrowser.open(url)
            print(f"[Player] Opened URL: {url}")
            
        elif t == "http_request":
            import urllib.request
            url = self.variables.substitute(event.value) if hasattr(self, 'variables') else event.value
            try:
                response = urllib.request.urlopen(url)
                if event.variable_name and hasattr(self, 'variables'):
                    self.variables.set(event.variable_name, response.read().decode('utf-8'))
                print(f"[Player] HTTP GET {url} OK")
            except Exception as exc:
                print(f"[Player] HTTP GET error: {exc}")

        else:
            if t not in ("end_if", "loop_start", "loop_end", "try_catch"):
                print(f"[Player] Unknown system event type: {t}")

    @staticmethod
    def _parse_combo_key(name: str):
        """Map common key names to pynput Key enum values."""
        _COMBO_MAP = {
            "ctrl":  Key.ctrl_l,  "control": Key.ctrl_l,
            "alt":   Key.alt_l,   "option":  Key.alt_l,
            "shift": Key.shift,
            "win":   Key.cmd,     "cmd":     Key.cmd,     "super": Key.cmd,
            "tab":   Key.tab,     "enter":   Key.enter,   "return": Key.enter,
            "esc":   Key.esc,     "escape":  Key.esc,
            "space": Key.space,
            "backspace": Key.backspace, "delete": Key.delete,
            "home": Key.home, "end": Key.end,
            "pageup": Key.page_up, "pagedown": Key.page_down,
            "up": Key.up, "down": Key.down, "left": Key.left, "right": Key.right,
            "f1": Key.f1, "f2": Key.f2, "f3": Key.f3, "f4": Key.f4,
            "f5": Key.f5, "f6": Key.f6, "f7": Key.f7, "f8": Key.f8,
            "f9": Key.f9, "f10": Key.f10, "f11": Key.f11, "f12": Key.f12,
        }
        return _COMBO_MAP.get(name, name)  # fallback: single char
