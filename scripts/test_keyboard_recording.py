"""
Keyboard recording integration test.

Records 5 seconds of mouse + keyboard activity, prints a breakdown,
saves to kb_test.json, then replays once.
"""

import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.recorder import Recorder
from core.player import Player
from core.event_model import MouseEvent, KeyboardEvent
from storage.macro_store import MacroStore
from config import MACROS_DIR


def main():
    print("=" * 60)
    print("  Keyboard Recording Integration Test")
    print("=" * 60)

    # ── 1. Record for 5 seconds ────────────────────────────
    recorder = Recorder()

    print("\n>>> Recording starts in 2 seconds — move mouse & press keys!")
    time.sleep(2)

    recorder.start()
    time.sleep(5)
    events = recorder.stop()

    # ── 2. Breakdown ────────────────────────────────────────
    mouse_events = [e for e in events if isinstance(e, MouseEvent)]
    kb_events = [e for e in events if isinstance(e, KeyboardEvent)]

    print("\n--- Event Breakdown ---")
    print(f"  Total events:    {len(events)}")
    print(f"  Mouse events:    {len(mouse_events)}")
    print(f"  Keyboard events: {len(kb_events)}")

    if mouse_events:
        moves = sum(1 for e in mouse_events if e.type == "move")
        clicks = sum(1 for e in mouse_events if e.type == "click")
        scrolls = sum(1 for e in mouse_events if e.type == "scroll")
        print(f"    ├─ moves:   {moves}")
        print(f"    ├─ clicks:  {clicks}")
        print(f"    └─ scrolls: {scrolls}")

    if kb_events:
        presses = sum(1 for e in kb_events if e.type == "key_press")
        releases = sum(1 for e in kb_events if e.type == "key_release")
        print(f"    ├─ key_press:   {presses}")
        print(f"    └─ key_release: {releases}")

        print("\n--- Keyboard Events ---")
        for e in kb_events:
            action = "↓" if e.type == "key_press" else "↑"
            print(f"  {action} {e.key:20s} @ {e.timestamp:.3f}s")
    else:
        print("\n  (no keyboard events captured — did you press any keys?)")

    # ── 3. Save to kb_test.json ─────────────────────────────
    store = MacroStore(MACROS_DIR)
    store.save("kb_test", events)
    print("\n>>> Saved to kb_test.json")

    # ── 4. Load and verify ──────────────────────────────────
    loaded = store.load("kb_test")
    loaded_kb = [e for e in loaded if isinstance(e, KeyboardEvent)]
    print(f">>> Loaded back: {len(loaded)} events ({len(loaded_kb)} keyboard)")
    assert len(loaded) == len(events), "Event count mismatch after load!"

    # ── 5. Replay once ──────────────────────────────────────
    print("\n>>> Replaying in 2 seconds...")
    time.sleep(2)

    player = Player()
    player.replay(events, loops=1)
    player.wait_until_done(timeout=30)

    print("\n>>> Replay complete!")
    print("=" * 60)
    print("  keyboard recording test PASSED")
    print("=" * 60)


if __name__ == "__main__":
    main()
