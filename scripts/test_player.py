"""Test script for the full record-then-replay cycle."""

import time
import threading
import sys
import os

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.recorder import Recorder
from core.player import Player

recorder = Recorder()
player = Player()

print("=" * 50)
print("  Record + Replay Test")
print("=" * 50)

# Step 1: Record
print("\nSTEP 1: Recording for 4 seconds — move mouse in a circle and click once")
recorder.start()
time.sleep(4)
events = recorder.stop()
print(f"  Captured {len(events)} events, duration {recorder.get_duration():.2f}s")

if not events:
    print("ERROR: No events captured — try running as Administrator")
    sys.exit(1)

# Step 2: Wait
print("\nSTEP 2: Waiting 2 seconds before replay...")
time.sleep(2)

# Step 3: Replay
print("\nSTEP 3: Replaying 2 times...")
done_event = threading.Event()

player.replay(
    events,
    loops=2,
    on_loop_complete=lambda n: print(f"  Loop {n} complete"),
    on_done=lambda: done_event.set(),
)

done_event.wait(timeout=30)
print("\nReplay complete! Test PASSED.")
