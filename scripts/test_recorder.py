"""Test script for core/recorder.py — records 5 seconds of mouse activity."""

import time
import sys
import os

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.recorder import Recorder

recorder = Recorder()

print("=" * 50)
print("  Recorder Test")
print("=" * 50)
print("Move your mouse around and click for 5 seconds...")
print()

recorder.start()
time.sleep(5)
events = recorder.stop()

print(f"\nTotal events captured: {len(events)}")

# Breakdown by type
move_count   = sum(1 for e in events if e.type == "move")
click_count  = sum(1 for e in events if e.type == "click")
scroll_count = sum(1 for e in events if e.type == "scroll")
print(f"  Move:   {move_count}")
print(f"  Click:  {click_count}")
print(f"  Scroll: {scroll_count}")

# First 5 events
print("\nFirst 5 events:")
for i, e in enumerate(events[:5]):
    print(f"  {i}: {e.type:6} at ({e.x:5}, {e.y:5})  t={e.timestamp:.3f}s")

# Last 5 events
if len(events) > 5:
    print("\nLast 5 events:")
    for i, e in enumerate(events[-5:], start=len(events) - 5):
        print(f"  {i}: {e.type:6} at ({e.x:5}, {e.y:5})  t={e.timestamp:.3f}s")

print(f"\nRecording duration: {recorder.get_duration():.2f}s")

assert len(events) > 0, "ERROR: No events captured — try running as Administrator"
print("\nrecorder test PASSED")
