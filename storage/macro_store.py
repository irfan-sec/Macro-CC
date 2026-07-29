"""
Macro persistence layer.

Saves and loads macros as human-readable JSON files.
Manages a library of named macros in the storage/macros/ directory.
"""

import os
import json
from datetime import datetime
from core.event_model import MouseEvent, KeyboardEvent, event_from_dict


class MacroStore:
    """
    Manages saving, loading, listing, and deleting macros.
    Each macro is stored as a .json file in the macros directory.
    """

    def __init__(self, macros_dir: str):
        self.macros_dir = macros_dir
        os.makedirs(macros_dir, exist_ok=True)

    # ── Core Operations ──────────────────────────────────────

    def save(self, name: str, events: list) -> str:
        """
        Save a macro to disk.
        Returns the full file path.
        """
        name = self._sanitize_name(name)
        filepath = self._filepath(name)

        metadata = {
            "name": name,
            "saved_at": datetime.now().isoformat(),
            "event_count": len(events),
            "duration_seconds": round(events[-1].timestamp, 3) if events else 0,
        }

        data = {
            "metadata": metadata,
            "events": [e.to_dict() for e in events],
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        print(f"[MacroStore] Saved '{name}' → {filepath}")
        return filepath

    def load(self, name: str) -> list:
        """
        Load a macro from disk.
        Returns empty list if macro doesn't exist.
        """
        name = self._sanitize_name(name)
        filepath = self._filepath(name)

        if not os.path.exists(filepath):
            print(f"[MacroStore] Not found: '{name}'")
            return []

        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        events = [event_from_dict(e) for e in data["events"]]
        meta = data.get("metadata", {})
        print(f"[MacroStore] Loaded '{name}' — {len(events)} events, {meta.get('duration_seconds', '?')}s")
        return events

    def delete(self, name: str) -> bool:
        """Delete a macro. Returns True if deleted, False if not found."""
        name = self._sanitize_name(name)
        filepath = self._filepath(name)

        if not os.path.exists(filepath):
            print(f"[MacroStore] Delete failed: '{name}' not found")
            return False

        os.remove(filepath)
        print(f"[MacroStore] Deleted '{name}'")
        return True

    def rename(self, old_name: str, new_name: str) -> bool:
        """Rename a macro file and update its internal metadata."""
        old_sanitized = self._sanitize_name(old_name)
        new_sanitized = self._sanitize_name(new_name)
        old_path = self._filepath(old_sanitized)
        new_path = self._filepath(new_sanitized)

        if not os.path.exists(old_path):
            print(f"[MacroStore] Rename failed: '{old_name}' not found")
            return False

        if os.path.exists(new_path):
            print(f"[MacroStore] Rename failed: '{new_name}' already exists")
            return False

        # Update the name inside the JSON metadata before renaming file
        try:
            with open(old_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if "metadata" in data:
                data["metadata"]["name"] = new_sanitized
            with open(old_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as exc:
            print(f"[MacroStore] Warning: could not update metadata: {exc}")

        os.rename(old_path, new_path)
        print(f"[MacroStore] Renamed '{old_name}' → '{new_name}'")
        return True

    # ── Listing ───────────────────────────────────────────────

    def list_all(self) -> list[dict]:
        """
        Returns list of all saved macros with metadata.
        Each item: { name, event_count, duration_seconds, saved_at, filepath }
        Sorted by saved_at descending (newest first).
        """
        macros = []

        for filename in os.listdir(self.macros_dir):
            if not filename.endswith(".json"):
                continue

            filepath = os.path.join(self.macros_dir, filename)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                meta = data.get("metadata", {})
                macros.append({
                    "name": meta.get("name", filename[:-5]),
                    "event_count": meta.get("event_count", len(data.get("events", []))),
                    "duration_seconds": meta.get("duration_seconds", 0),
                    "saved_at": meta.get("saved_at", "unknown"),
                    "filepath": filepath,
                })
            except (json.JSONDecodeError, KeyError):
                print(f"[MacroStore] Warning: Could not read {filename}")

        return sorted(macros, key=lambda m: m["saved_at"], reverse=True)

    def exists(self, name: str) -> bool:
        """Check if a macro exists on disk."""
        return os.path.exists(self._filepath(self._sanitize_name(name)))

    # ── Helpers ───────────────────────────────────────────────

    def _filepath(self, name: str) -> str:
        """Return full path for a macro name."""
        return os.path.join(self.macros_dir, f"{name}.json")

    def _sanitize_name(self, name: str) -> str:
        """Remove characters not safe for filenames."""
        safe = "".join(c for c in name if c.isalnum() or c in "-_ ")
        return safe.strip().replace(" ", "_") or "unnamed"
