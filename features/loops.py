"""
Loop runner for macro playback.

Supports count-based, infinite, and timed loop modes.
All modes run in background daemon threads and can be interrupted.
"""

import time
import threading
from core.player import Player
from core.event_model import MouseEvent


class LoopRunner:
    """
    Wraps Player to support flexible loop modes.

    Modes:
    - count:    Play exactly N times
    - infinite: Play until stop() is called
    - timed:    Play for up to X seconds
    """

    def __init__(self, player: Player):
        self.player = player
        self._stop_flag = threading.Event()
        self.is_running = False

    def run_count(self, events: list[MouseEvent], count: int, delay_between: float = 0.0):
        """Play `count` times with optional pause between loops."""
        self._stop_flag.clear()
        self.is_running = True

        def worker():
            try:
                for i in range(count):
                    if self._stop_flag.is_set():
                        break
                    print(f"[LoopRunner] Loop {i + 1}/{count}")
                    self.player.replay(events, loops=1)
                    self.player.wait_until_done()

                    # Pause between loops
                    if delay_between > 0 and i < count - 1:
                        self._interruptible_sleep(delay_between)

                print("[LoopRunner] Done")
            finally:
                self.is_running = False

        threading.Thread(target=worker, daemon=True).start()

    def run_infinite(self, events: list[MouseEvent], delay_between: float = 0.0):
        """Play forever until stop() is called."""
        self._stop_flag.clear()
        self.is_running = True

        def worker():
            loop_num = 0
            try:
                while not self._stop_flag.is_set():
                    loop_num += 1
                    print(f"[LoopRunner] Loop {loop_num} (infinite)")
                    self.player.replay(events, loops=1)
                    self.player.wait_until_done()

                    if delay_between > 0:
                        self._interruptible_sleep(delay_between)
            finally:
                self.is_running = False

        threading.Thread(target=worker, daemon=True).start()

    def run_timed(self, events: list[MouseEvent], duration_seconds: float):
        """Play repeatedly for up to `duration_seconds` total time."""
        self._stop_flag.clear()
        self.is_running = True
        end_time = time.perf_counter() + duration_seconds

        def worker():
            try:
                while time.perf_counter() < end_time and not self._stop_flag.is_set():
                    self.player.replay(events, loops=1)
                    self.player.wait_until_done()

                print(f"[LoopRunner] Timed run complete ({duration_seconds}s)")
            finally:
                self.is_running = False

        threading.Thread(target=worker, daemon=True).start()

    def stop(self):
        """Stop the current loop run."""
        self._stop_flag.set()
        self.player.abort()
        self.is_running = False

    def _interruptible_sleep(self, seconds: float):
        """Sleep that can be interrupted by stop()."""
        end = time.perf_counter() + seconds
        while time.perf_counter() < end:
            if self._stop_flag.is_set():
                break
            time.sleep(0.05)
