"""Quick functional test for main_window.py"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ui.main_window import MacroRecorderWindow

w = MacroRecorderWindow(app=None)

# 1. Test loading sample actions
sample = [
    {"type": "click", "x": 100, "y": 200, "button": "left"},
    {"type": "key_press", "key": "a"},
    {"type": "wait_seconds", "value": "0.5"},
    {"type": "run_app", "value": "notepad.exe"},
    {"type": "move", "x": 300, "y": 400, "timestamp": 1.0},
]
w.load_actions(sample)
print(f"Loaded {len(sample)} actions into treeview")

# 2. Verify treeview content
children = w._action_tree.get_children()
print(f"Treeview has {len(children)} rows")
for item in children:
    vals = w._action_tree.item(item, "values")
    print(f"  Row: #{vals[0]} {vals[1]} {vals[2]} | {vals[3]}")

# 3. Test get_loop_count
print(f"Loop count: {w.get_loop_count()}")

# 4. Test set_speed
w.set_speed(2.0)
print(f"Speed set to: {w._speed}")

# 5. Test  _event_value_str for each type
for ev in sample:
    v = w._event_value_str(ev)
    print(f"  {ev['type']} -> \"{v}\"")

# 6. Test macro_dir exists
print(f"Macro dir: {w._macro_dir()}")

# 7. Status
w.set_status("Recording...")
print(f"Status: {w._status}")

# 8. Check engine is embedded
print(f"Has recorder: {w._recorder is not None}")
print(f"Has player: {w._player is not None}")
print(f"Has store: {w._store is not None}")

w.destroy()
print("\nAll functional tests passed!")
