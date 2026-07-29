"""
Search & Replace dialog for the macro action list.
Dark‑themed modal window matching ui/theme.py.
"""

import re
import tkinter as tk
from tkinter import ttk
from typing import Optional

import sys
from pathlib import Path

_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from ui.theme import (
    BG_PRIMARY, BG_SECONDARY, ACCENT, ACCENT_HOVER,
    TEXT_COLOR, TEXT_DIM, BORDER_COLOR,
    FONT_MAIN, FONT_SMALL, FONT_BOLD, FONT_HEADER,
)


class SearchReplaceDialog(tk.Toplevel):
    """Modal Search & Replace dialog for the action Treeview."""

    def __init__(self, parent: tk.Misc, action_tree: ttk.Treeview):
        super().__init__(parent)
        self.title("Search & Replace Actions")
        self.configure(bg=BG_PRIMARY)
        self.geometry("440x310")
        self.minsize(400, 280)
        self.resizable(True, False)
        self.transient(parent)

        self._tree = action_tree
        self._matches: list[str] = []      # item IDs that matched
        self._match_idx: int = -1          # current position in _matches

        # ── Variables ────────────────────────────────────────
        self._search_var = tk.StringVar()
        self._replace_var = tk.StringVar()
        self._field_var = tk.StringVar(value="All fields")
        self._case_var = tk.BooleanVar(value=False)
        self._whole_var = tk.BooleanVar(value=False)
        self._regex_var = tk.BooleanVar(value=False)

        self._build_ui()

        # Centre on parent
        self.update_idletasks()
        px = parent.winfo_rootx() + (parent.winfo_width() - self.winfo_width()) // 2
        py = parent.winfo_rooty() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{max(px, 0)}+{max(py, 0)}")

        # Focus the search field
        self._search_entry.focus_set()
        self.bind("<Return>", lambda e: self._find_next())
        self.bind("<Escape>", lambda e: self._on_close())

    # ══════════════════════════════════════════════════════════
    # UI
    # ══════════════════════════════════════════════════════════
    def _build_ui(self):
        pad = {"padx": 14, "pady": (0, 4)}

        # ── Search ───────────────────────────────────────────
        tk.Label(self, text="Search:", font=FONT_BOLD,
                 bg=BG_PRIMARY, fg=TEXT_COLOR, anchor="w").pack(fill="x", padx=14, pady=(12, 2))
        self._search_entry = tk.Entry(
            self, textvariable=self._search_var,
            bg=BG_SECONDARY, fg=TEXT_COLOR, insertbackground=TEXT_COLOR,
            font=FONT_MAIN, relief="flat", bd=0,
        )
        self._search_entry.pack(fill="x", **pad, ipady=4)

        # ── Replace ──────────────────────────────────────────
        tk.Label(self, text="Replace with:", font=FONT_BOLD,
                 bg=BG_PRIMARY, fg=TEXT_COLOR, anchor="w").pack(fill="x", **pad)
        tk.Entry(
            self, textvariable=self._replace_var,
            bg=BG_SECONDARY, fg=TEXT_COLOR, insertbackground=TEXT_COLOR,
            font=FONT_MAIN, relief="flat", bd=0,
        ).pack(fill="x", **pad, ipady=4)

        # ── Options row ──────────────────────────────────────
        opts = tk.Frame(self, bg=BG_PRIMARY)
        opts.pack(fill="x", padx=14, pady=(6, 2))

        tk.Label(opts, text="Search in:", font=FONT_SMALL,
                 bg=BG_PRIMARY, fg=TEXT_DIM).pack(side="left")
        field_combo = ttk.Combobox(
            opts, textvariable=self._field_var, state="readonly", width=14,
            values=["All fields", "Action type", "Value", "Comment"],
        )
        field_combo.pack(side="left", padx=(6, 12))

        tk.Checkbutton(opts, text="Case sensitive", variable=self._case_var,
                        bg=BG_PRIMARY, fg=TEXT_DIM, activebackground=BG_PRIMARY,
                        activeforeground=TEXT_COLOR, selectcolor=BG_SECONDARY,
                        font=FONT_SMALL).pack(side="left")
        tk.Checkbutton(opts, text="Whole word", variable=self._whole_var,
                        bg=BG_PRIMARY, fg=TEXT_DIM, activebackground=BG_PRIMARY,
                        activeforeground=TEXT_COLOR, selectcolor=BG_SECONDARY,
                        font=FONT_SMALL).pack(side="left")
        tk.Checkbutton(opts, text="Regex", variable=self._regex_var,
                        bg=BG_PRIMARY, fg=TEXT_DIM, activebackground=BG_PRIMARY,
                        activeforeground=TEXT_COLOR, selectcolor=BG_SECONDARY,
                        font=FONT_SMALL).pack(side="left")

        # ── Result label ─────────────────────────────────────
        self._result_label = tk.Label(
            self, text="", font=FONT_SMALL,
            bg=BG_PRIMARY, fg=TEXT_DIM, anchor="w",
        )
        self._result_label.pack(fill="x", padx=14, pady=(4, 6))

        # ── Buttons ──────────────────────────────────────────
        btn_bar = tk.Frame(self, bg=BG_PRIMARY)
        btn_bar.pack(fill="x", padx=14, pady=(4, 12))

        btn_style = dict(
            font=FONT_MAIN, relief="flat", bd=0, cursor="hand2",
            bg=BG_SECONDARY, fg=TEXT_COLOR, activebackground=ACCENT,
            activeforeground=TEXT_COLOR, width=12,
        )

        tk.Button(btn_bar, text="Close", command=self._on_close,
                  **btn_style).pack(side="right", padx=(6, 0), ipady=4)
        tk.Button(btn_bar, text="Replace All", command=self._replace_all,
                  **btn_style).pack(side="right", padx=(6, 0), ipady=4)
        tk.Button(btn_bar, text="Replace", command=self._replace_one,
                  **btn_style).pack(side="right", padx=(6, 0), ipady=4)
        tk.Button(btn_bar, text="Find Next", command=self._find_next,
                  bg=ACCENT, fg=TEXT_COLOR, activebackground=ACCENT_HOVER,
                  activeforeground=TEXT_COLOR, font=FONT_BOLD, relief="flat",
                  bd=0, cursor="hand2", width=12).pack(
            side="right", ipady=4)

    # ══════════════════════════════════════════════════════════
    # Search logic
    # ══════════════════════════════════════════════════════════
    def _build_pattern(self) -> Optional[re.Pattern]:
        raw = self._search_var.get()
        if not raw:
            return None

        flags = 0 if self._case_var.get() else re.IGNORECASE

        if not self._regex_var.get():
            raw = re.escape(raw)
        if self._whole_var.get():
            raw = rf"\b{raw}\b"

        try:
            return re.compile(raw, flags)
        except re.error:
            self._result_label.config(text="Invalid regex", fg=ACCENT)
            return None

    def _col_indices(self) -> list[int]:
        """Return Treeview value indices to search in."""
        field = self._field_var.get()
        if field == "Action type":
            return [2]
        if field == "Value":
            return [3]
        if field == "Comment":
            return [4]
        return [2, 3, 4]  # All fields

    def _find_all(self):
        """Populate self._matches with all matching item IDs."""
        pattern = self._build_pattern()
        if not pattern:
            self._matches.clear()
            self._match_idx = -1
            self._result_label.config(text="", fg=TEXT_DIM)
            return

        cols = self._col_indices()
        self._matches.clear()

        # Clear previous highlights
        for item in self._tree.get_children():
            tags = list(self._tree.item(item, "tags"))
            if "search_match" in tags:
                tags.remove("search_match")
                self._tree.item(item, tags=tags)

        for item in self._tree.get_children():
            vals = self._tree.item(item, "values")
            for ci in cols:
                if ci < len(vals) and pattern.search(str(vals[ci])):
                    self._matches.append(item)
                    tags = list(self._tree.item(item, "tags"))
                    tags.append("search_match")
                    self._tree.item(item, tags=tags)
                    break

        self._tree.tag_configure("search_match", background="#3a3a5e")

        n = len(self._matches)
        self._result_label.config(
            text=f"{n} match{'es' if n != 1 else ''} found" if n else "No matches",
            fg=TEXT_COLOR if n else TEXT_DIM,
        )
        self._match_idx = -1

    def _find_next(self):
        self._find_all()
        if not self._matches:
            return
        self._match_idx = (self._match_idx + 1) % len(self._matches)
        item = self._matches[self._match_idx]
        self._tree.selection_set(item)
        self._tree.see(item)
        self._result_label.config(
            text=f"Match {self._match_idx + 1} of {len(self._matches)}",
            fg=TEXT_COLOR,
        )

    def _replace_one(self):
        """Replace the current match."""
        if not self._matches or self._match_idx < 0:
            self._find_next()
            return

        item = self._matches[self._match_idx]
        self._do_replace(item)
        self._find_all()

    def _replace_all(self):
        """Replace all matches."""
        self._find_all()
        if not self._matches:
            return
        count = 0
        for item in list(self._matches):
            if self._do_replace(item):
                count += 1
        self._result_label.config(
            text=f"Replaced {count} match{'es' if count != 1 else ''}",
            fg=TEXT_COLOR,
        )
        self._find_all()

    def _do_replace(self, item: str) -> bool:
        """Perform the replacement on a single tree item. Returns True if changed."""
        pattern = self._build_pattern()
        if not pattern:
            return False

        repl = self._replace_var.get()
        cols = self._col_indices()
        vals = list(self._tree.item(item, "values"))
        changed = False

        for ci in cols:
            if ci < len(vals):
                old = str(vals[ci])
                new = pattern.sub(repl, old)
                if new != old:
                    vals[ci] = new
                    changed = True

        if changed:
            self._tree.item(item, values=vals)
        return changed

    def _on_close(self):
        # Clean up search_match tags
        for item in self._tree.get_children():
            tags = list(self._tree.item(item, "tags"))
            if "search_match" in tags:
                tags.remove("search_match")
                self._tree.item(item, tags=tags)
        self.destroy()


# ───────────────────────────────────────────────────────────────
# Convenience function
# ───────────────────────────────────────────────────────────────
def open_search_replace(parent: tk.Misc, action_tree: ttk.Treeview):
    """Open the Search & Replace dialog (non‑modal, stays on top)."""
    dlg = SearchReplaceDialog(parent, action_tree)
    dlg.focus_force()
