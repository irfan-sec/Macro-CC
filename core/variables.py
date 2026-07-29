"""
Variable Store — key‑value storage with placeholder substitution.

Macros can save values with {variable_name} placeholders and
have them substituted at replay time.
"""

import re
import os
from typing import Optional


class VariableStore:
    """
    In‑memory key=value store with file persistence and template substitution.

    Usage:
        vs = VariableStore()
        vs.set("name", "John")
        vs.substitute("Hello {name}!")  # → "Hello John!"
    """

    def __init__(self):
        self._vars: dict[str, str] = {}

    # ── Core CRUD ────────────────────────────────────────────

    def set(self, name: str, value: str) -> None:
        """Store a variable."""
        self._vars[name] = value

    def get(self, name: str, default: str = "") -> str:
        """Retrieve a variable, returning *default* if not found."""
        return self._vars.get(name, default)

    def get_all(self) -> dict[str, str]:
        """Return a shallow copy of all variables."""
        return dict(self._vars)

    def clear(self) -> None:
        """Delete all stored variables."""
        self._vars.clear()

    # ── File I/O ──────────────────────────────────────────────

    def save_to_file(self, path: str) -> None:
        """Write all variables as ``key=value`` lines to a text file."""
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            for k, v in sorted(self._vars.items()):
                # Escape newlines so we keep one variable per line
                f.write(f"{k}={v.replace(chr(10), '\\n')}\n")

    def load_from_file(self, path: str) -> None:
        """Read ``key=value`` lines from a text file into memory."""
        if not os.path.exists(path):
            return
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.rstrip("\n")
                if "=" not in line:
                    continue
                key, value = line.split("=", 1)
                self._vars[key] = value.replace("\\n", "\n")

    # ── Template substitution ─────────────────────────────────

    def substitute(self, text: str) -> str:
        """
        Replace ``{variable_name}`` placeholders in *text* with stored values.

        Unknown variables are left unchanged.
        """
        def _replacer(m: re.Match) -> str:
            name = m.group(1)
            return self._vars.get(name, m.group(0))

        return re.sub(r"\{(\w+)\}", _replacer, text)

    # ── Dunder helpers ────────────────────────────────────────

    def __len__(self) -> int:
        return len(self._vars)

    def __repr__(self) -> str:
        return f"VariableStore({self._vars!r})"


# ───────────────────────────────────────────────────────────────
# Quick self‑test
# ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    vs = VariableStore()
    vs.set("user", "Alice")
    vs.set("greeting", "Hello")
    assert vs.get("user") == "Alice"
    assert vs.get("missing", "default") == "default"
    assert vs.substitute("{greeting} {user}!") == "Hello Alice!"
    assert vs.substitute("No vars here") == "No vars here"
    assert vs.substitute("{unknown} stays") == "{unknown} stays"
    assert len(vs.get_all()) == 2

    # File round‑trip
    import tempfile
    tmp = os.path.join(tempfile.gettempdir(), "vs_test.txt")
    vs.save_to_file(tmp)
    vs2 = VariableStore()
    vs2.load_from_file(tmp)
    assert vs2.get_all() == vs.get_all()
    os.remove(tmp)

    vs.clear()
    assert len(vs) == 0

    print("variables.py OK")
