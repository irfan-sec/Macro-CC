"""Test script for storage/macro_store.py — tests save, load, list, rename, delete."""

import sys
import os

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from storage.macro_store import MacroStore
from core.event_model import MouseEvent

print("=" * 50)
print("  Storage Test")
print("=" * 50)

store = MacroStore("storage/macros")

# Create 5 fake events
events = [
    MouseEvent("move",   100, 200, 0.0),
    MouseEvent("move",   150, 250, 0.5),
    MouseEvent("click",  200, 300, 1.0, button="left", pressed=True),
    MouseEvent("click",  200, 300, 1.1, button="left", pressed=False),
    MouseEvent("scroll", 200, 300, 1.5, dx=0, dy=-3),
]

# Test save
print("\n1. Testing save()...")
filepath = store.save("test_storage_macro", events)
assert os.path.exists(filepath), f"File not found: {filepath}"
print("   ✅ save() OK — file exists on disk")

# Test load
print("\n2. Testing load()...")
loaded = store.load("test_storage_macro")
assert len(loaded) == len(events), f"Expected {len(events)} events, got {len(loaded)}"
print(f"   ✅ load() OK — {len(loaded)} events loaded")

# Test list_all
print("\n3. Testing list_all()...")
all_macros = store.list_all()
names = [m["name"] for m in all_macros]
assert "test_storage_macro" in names, "Macro not found in list_all()"
print(f"   ✅ list_all() OK — found {len(all_macros)} macro(s)")

# Test rename
print("\n4. Testing rename()...")
result = store.rename("test_storage_macro", "test_renamed_macro")
assert result is True, "Rename failed"
assert not store.exists("test_storage_macro"), "Old name still exists"
assert store.exists("test_renamed_macro"), "New name not found"
print("   ✅ rename() OK")

# Test delete
print("\n5. Testing delete()...")
result = store.delete("test_renamed_macro")
assert result is True, "Delete failed"
assert not store.exists("test_renamed_macro"), "File still exists after delete"
print("   ✅ delete() OK")

# Test load on deleted macro
print("\n6. Testing load() on deleted macro...")
loaded = store.load("test_renamed_macro")
assert loaded == [], f"Expected empty list, got {len(loaded)} events"
print("   ✅ load() on deleted macro returns empty list (no crash)")

print("\n" + "=" * 50)
print("  storage tests PASSED")
print("=" * 50)
