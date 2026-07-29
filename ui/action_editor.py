"""
Action Editor Dialog — modal window for adding / editing individual macro actions.
Matches the dark theme from ui/main_window.py.
"""

import tkinter as tk
from tkinter import ttk, filedialog
from typing import Optional

# ---------------------------------------------------------------------------
# Theme constants (shared via ui/theme.py to avoid circular imports)
# ---------------------------------------------------------------------------
from ui.theme import (
    BG_PRIMARY, BG_SECONDARY, ACCENT, ACCENT_HOVER,
    TEXT_COLOR, TEXT_DIM, BORDER_COLOR,
    FONT_MAIN, FONT_SMALL, FONT_BOLD, FONT_HEADER, FONT_MONO,
)
from ui.coordinate_picker import CoordinatePicker

# ---------------------------------------------------------------------------
# Action catalogue — (category_emoji, category_label, [(action_id, label), …])
# ---------------------------------------------------------------------------
ACTION_CATALOGUE: list[tuple[str, str, list[tuple[str, str]]]] = [
    ("🖱", "Mouse", [
        ("mouse_move",   "Mouse Move"),
        ("left_click",   "Left Click"),
        ("right_click",  "Right Click"),
        ("double_click", "Double Click"),
        ("scroll_up",    "Scroll Up"),
        ("scroll_down",  "Scroll Down"),
    ]),
    ("⌨", "Keyboard", [
        ("type_text",    "Type Text"),
        ("key_press",    "Key Press"),
        ("key_combo",    "Key Combination"),
    ]),
    ("⏱", "Control", [
        ("wait",               "Wait (seconds)"),
        ("wait_screen_change", "Wait for Screen Change"),
        ("repeat_loop",        "Repeat / Loop"),
    ]),
    ("🔍", "Search", [
        ("find_image", "Find Image on Screen"),
        ("find_text",  "Find Text (OCR)"),
    ]),
    ("💾", "System", [
        ("run_app",      "Run Application"),
        ("save_variable","Save Variable"),
        ("window_focus", "Window Focus"),
    ]),
]

# Flat lookup: action_id → (category, label)
_ACTION_META: dict[str, tuple[str, str]] = {}
for _cat_emoji, _cat_label, _actions in ACTION_CATALOGUE:
    for _aid, _alabel in _actions:
        _ACTION_META[_aid] = (_cat_label, _alabel)


class ActionEditorDialog(tk.Toplevel):
    """Modal dialog for creating or editing a single macro action."""

    def __init__(
        self,
        parent: tk.Misc,
        *,
        action: Optional[dict] = None,
        title: str = "Edit Action",
    ):
        """
        Parameters
        ----------
        parent : tk.Misc
            The parent widget (usually the MacroRecorderWindow).
        action : dict | None
            If editing, pass the existing action dict.
            If adding a new action, pass ``None``.
        title : str
            Window title.
        """
        super().__init__(parent)
        self.title(title)
        self.configure(bg=BG_PRIMARY)
        self.geometry("620x480")
        self.minsize(560, 420)
        self.resizable(True, True)

        # Make modal
        self.transient(parent)
        self.grab_set()

        # Result: set by _on_confirm, read by caller after .wait_window()
        self.result: Optional[dict] = None

        # Existing action being edited (None ⇒ "Add" mode)
        self._editing = action
        self._is_edit = action is not None

        # Currently selected action_id
        self._selected_id: Optional[str] = None

        # Track dynamically‑created form widgets so we can read their values
        self._form_vars: dict[str, tk.Variable] = {}
        self._form_widgets: dict[str, tk.Widget] = {}

        # Expanded categories (by category label)
        self._expanded: dict[str, bool] = {cat: True for _, cat, _ in ACTION_CATALOGUE}

        # ----- Build UI ---------------------------------------------------
        self._build_type_selector()
        self._build_right_panel()
        self._build_buttons()

        # If editing, pre‑select the action type & populate fields
        if self._editing:
            self._preselect(self._editing)

        # Centre on parent
        self.update_idletasks()
        px = parent.winfo_rootx() + (parent.winfo_width() - self.winfo_width()) // 2
        py = parent.winfo_rooty() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{max(px, 0)}+{max(py, 0)}")

    # ===================================================================
    # Left panel — categorised action type selector
    # ===================================================================
    def _build_type_selector(self):
        left = tk.Frame(self, bg=BG_SECONDARY, width=190)
        left.pack(side="left", fill="y", padx=(0, 0))
        left.pack_propagate(False)

        header = tk.Label(left, text="Action Type", font=FONT_BOLD,
                          bg=BG_SECONDARY, fg=TEXT_COLOR, anchor="w")
        header.pack(fill="x", padx=10, pady=(10, 4))

        # Scrollable canvas for the category tree
        canvas_frame = tk.Frame(left, bg=BG_SECONDARY)
        canvas_frame.pack(fill="both", expand=True, padx=4, pady=(0, 4))

        canvas = tk.Canvas(canvas_frame, bg=BG_SECONDARY,
                           highlightthickness=0, bd=0)
        scrollbar = tk.Scrollbar(canvas_frame, orient="vertical",
                                 command=canvas.yview,
                                 bg=BG_SECONDARY, troughcolor=BG_PRIMARY,
                                 highlightthickness=0, bd=0)
        self._type_inner = tk.Frame(canvas, bg=BG_SECONDARY)

        self._type_inner.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        canvas.create_window((0, 0), window=self._type_inner, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Bind mousewheel inside the canvas
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        canvas.bind_all("<MouseWheel>", _on_mousewheel, add="+")

        # Store references for row highlighting
        self._type_rows: dict[str, tk.Frame] = {}

        self._populate_type_list()

    def _populate_type_list(self):
        for w in self._type_inner.winfo_children():
            w.destroy()
        self._type_rows.clear()

        for cat_emoji, cat_label, actions in ACTION_CATALOGUE:
            expanded = self._expanded.get(cat_label, True)

            # Category header row
            cat_row = tk.Frame(self._type_inner, bg=BG_SECONDARY, cursor="hand2")
            cat_row.pack(fill="x", pady=(4, 0))

            arrow = "▾" if expanded else "▸"
            cat_btn = tk.Label(
                cat_row,
                text=f" {arrow}  {cat_emoji} {cat_label}",
                font=FONT_BOLD, bg=BG_SECONDARY, fg=TEXT_COLOR,
                anchor="w",
            )
            cat_btn.pack(fill="x", padx=4, ipady=2)

            # Click to toggle expansion
            def _toggle(lbl=cat_label):
                self._expanded[lbl] = not self._expanded[lbl]
                self._populate_type_list()

            cat_btn.bind("<Button-1>", lambda e, cb=_toggle: cb())
            cat_row.bind("<Button-1>", lambda e, cb=_toggle: cb())

            if not expanded:
                continue

            for action_id, action_label in actions:
                row = tk.Frame(self._type_inner, bg=BG_PRIMARY, cursor="hand2")
                row.pack(fill="x", padx=(16, 4), pady=1)

                lbl = tk.Label(
                    row, text=f"  {action_label}", font=FONT_MAIN,
                    bg=BG_PRIMARY, fg=TEXT_DIM, anchor="w",
                )
                lbl.pack(fill="x", ipady=3, padx=2)

                self._type_rows[action_id] = row

                def _select(aid=action_id, r=row):
                    self._on_type_select(aid)

                row.bind("<Button-1>", lambda e, cb=_select: cb())
                lbl.bind("<Button-1>", lambda e, cb=_select: cb())

                # Hover effect
                def _enter(e, r=row, l=lbl, aid=action_id):
                    if self._selected_id != aid:
                        r.configure(bg=BORDER_COLOR)
                        l.configure(bg=BORDER_COLOR, fg=TEXT_COLOR)

                def _leave(e, r=row, l=lbl, aid=action_id):
                    if self._selected_id != aid:
                        r.configure(bg=BG_PRIMARY)
                        l.configure(bg=BG_PRIMARY, fg=TEXT_DIM)

                row.bind("<Enter>", _enter)
                lbl.bind("<Enter>", _enter)
                row.bind("<Leave>", _leave)
                lbl.bind("<Leave>", _leave)

        # Re‑highlight current selection
        if self._selected_id:
            self._highlight_row(self._selected_id)

    def _highlight_row(self, action_id: str):
        for aid, row in self._type_rows.items():
            if aid == action_id:
                row.configure(bg=ACCENT)
                for child in row.winfo_children():
                    child.configure(bg=ACCENT, fg=TEXT_COLOR)
            else:
                row.configure(bg=BG_PRIMARY)
                for child in row.winfo_children():
                    child.configure(bg=BG_PRIMARY, fg=TEXT_DIM)

    def _on_type_select(self, action_id: str):
        self._selected_id = action_id
        self._highlight_row(action_id)
        self._build_form(action_id)

    # ===================================================================
    # Right panel — dynamic form area
    # ===================================================================
    def _build_right_panel(self):
        self._right = tk.Frame(self, bg=BG_PRIMARY)
        self._right.pack(side="left", fill="both", expand=True, padx=(4, 0))

        # Form container (rebuilt when action type changes)
        self._form_frame = tk.Frame(self._right, bg=BG_PRIMARY)
        self._form_frame.pack(fill="both", expand=True, padx=10, pady=(10, 0))

        # Placeholder
        self._placeholder = tk.Label(
            self._form_frame,
            text="← Select an action type",
            font=FONT_HEADER, bg=BG_PRIMARY, fg=TEXT_DIM,
        )
        self._placeholder.pack(expand=True)

    def _clear_form(self):
        for w in self._form_frame.winfo_children():
            w.destroy()
        self._form_vars.clear()
        self._form_widgets.clear()

    def _build_form(self, action_id: str):
        self._clear_form()

        _, label = _ACTION_META.get(action_id, ("", action_id))
        tk.Label(
            self._form_frame, text=label, font=FONT_HEADER,
            bg=BG_PRIMARY, fg=TEXT_COLOR, anchor="w",
        ).pack(fill="x", pady=(0, 8))

        # Separator
        tk.Frame(self._form_frame, bg=ACCENT, height=2).pack(fill="x", pady=(0, 10))

        # ---- per‑action fields ----------------------------------------
        builders = {
            "mouse_move":   self._form_mouse_move,
            "left_click":   self._form_click,
            "right_click":  self._form_click,
            "double_click": self._form_click,
            "scroll_up":    self._form_scroll,
            "scroll_down":  self._form_scroll,
            "type_text":    self._form_type_text,
            "key_press":    self._form_key_press,
            "key_combo":    self._form_key_combo,
            "wait":         self._form_wait,
            "wait_screen_change": self._form_wait_screen,
            "repeat_loop":  self._form_repeat,
            "find_image":   self._form_find_image,
            "find_text":    self._form_find_text,
            "run_app":      self._form_run_app,
            "save_variable":self._form_save_variable,
            "window_focus": self._form_window_focus,
        }

        builder = builders.get(action_id)
        if builder:
            builder(action_id)
        else:
            tk.Label(self._form_frame, text="(no parameters)",
                     font=FONT_MAIN, bg=BG_PRIMARY, fg=TEXT_DIM).pack()

        # ---- comment (always present) ---------------------------------
        tk.Frame(self._form_frame, bg=BORDER_COLOR, height=1).pack(
            fill="x", pady=(14, 6))
        tk.Label(self._form_frame, text="Comment", font=FONT_SMALL,
                 bg=BG_PRIMARY, fg=TEXT_DIM, anchor="w").pack(fill="x")
        comment_var = tk.StringVar(value=self._edit_val("comment", ""))
        self._form_vars["comment"] = comment_var
        tk.Entry(
            self._form_frame, textvariable=comment_var,
            bg=BG_SECONDARY, fg=TEXT_COLOR, insertbackground=TEXT_COLOR,
            font=FONT_MAIN, relief="flat", bd=0,
        ).pack(fill="x", ipady=4, pady=(2, 0))

    # ---- form helpers ---------------------------------------------------
    def _add_label(self, text: str):
        tk.Label(self._form_frame, text=text, font=FONT_SMALL,
                 bg=BG_PRIMARY, fg=TEXT_DIM, anchor="w").pack(fill="x", pady=(6, 0))

    def _add_entry(self, key: str, default: str = "") -> tk.Entry:
        var = tk.StringVar(value=self._edit_val(key, default))
        self._form_vars[key] = var
        entry = tk.Entry(
            self._form_frame, textvariable=var,
            bg=BG_SECONDARY, fg=TEXT_COLOR, insertbackground=TEXT_COLOR,
            font=FONT_MAIN, relief="flat", bd=0,
        )
        entry.pack(fill="x", ipady=4, pady=(2, 0))
        self._form_widgets[key] = entry
        return entry

    def _add_spinbox(self, key: str, from_: float = 0, to: float = 9999,
                     increment: float = 1, default: str = "1") -> tk.Spinbox:
        var = tk.StringVar(value=self._edit_val(key, default))
        self._form_vars[key] = var
        sb = tk.Spinbox(
            self._form_frame, textvariable=var,
            from_=from_, to=to, increment=increment,
            bg=BG_SECONDARY, fg=TEXT_COLOR, insertbackground=TEXT_COLOR,
            font=FONT_MAIN, relief="flat", bd=0, buttonbackground=BG_SECONDARY,
        )
        sb.pack(fill="x", ipady=4, pady=(2, 0))
        self._form_widgets[key] = sb
        return sb

    def _add_text(self, key: str, height: int = 4, default: str = "") -> tk.Text:
        txt = tk.Text(
            self._form_frame, height=height,
            bg=BG_SECONDARY, fg=TEXT_COLOR, insertbackground=TEXT_COLOR,
            font=FONT_MONO, relief="flat", bd=0, wrap="word",
        )
        txt.insert("1.0", self._edit_val(key, default))
        txt.pack(fill="both", expand=True, pady=(2, 0))
        self._form_widgets[key] = txt
        return txt

    def _edit_val(self, key: str, fallback):
        """Return an existing action value when editing, else *fallback*."""
        if self._editing and key in self._editing:
            return str(self._editing[key])
        return fallback

    # ---- per‑action form builders --------------------------------------

    def _form_mouse_move(self, _aid: str):
        row = tk.Frame(self._form_frame, bg=BG_PRIMARY)
        row.pack(fill="x")

        # X
        tk.Label(row, text="X", font=FONT_SMALL, bg=BG_PRIMARY,
                 fg=TEXT_DIM, width=4).pack(side="left")
        x_var = tk.StringVar(value=self._edit_val("x", "0"))
        self._form_vars["x"] = x_var
        tk.Entry(row, textvariable=x_var, width=8,
                 bg=BG_SECONDARY, fg=TEXT_COLOR, insertbackground=TEXT_COLOR,
                 font=FONT_MAIN, relief="flat", bd=0).pack(side="left", ipady=4, padx=(0, 10))

        # Y
        tk.Label(row, text="Y", font=FONT_SMALL, bg=BG_PRIMARY,
                 fg=TEXT_DIM, width=4).pack(side="left")
        y_var = tk.StringVar(value=self._edit_val("y", "0"))
        self._form_vars["y"] = y_var
        tk.Entry(row, textvariable=y_var, width=8,
                 bg=BG_SECONDARY, fg=TEXT_COLOR, insertbackground=TEXT_COLOR,
                 font=FONT_MAIN, relief="flat", bd=0).pack(side="left", ipady=4)

        # Pick button
        pick_btn = tk.Button(
            self._form_frame, text="🎯  Pick from screen", font=FONT_MAIN,
            bg=BG_SECONDARY, fg=TEXT_COLOR, activebackground=ACCENT,
            activeforeground=TEXT_COLOR, relief="flat", bd=0, cursor="hand2",
            command=lambda: self._pick_position(x_var, y_var),
        )
        pick_btn.pack(fill="x", pady=(8, 0), ipady=4)

        self._add_label("Duration (seconds)")
        self._add_spinbox("duration", from_=0, to=60, increment=0.05, default="0")

    def _form_click(self, aid: str):
        button_map = {
            "left_click": "left", "right_click": "right",
            "double_click": "left",
        }
        row = tk.Frame(self._form_frame, bg=BG_PRIMARY)
        row.pack(fill="x")

        tk.Label(row, text="X", font=FONT_SMALL, bg=BG_PRIMARY,
                 fg=TEXT_DIM, width=4).pack(side="left")
        x_var = tk.StringVar(value=self._edit_val("x", "0"))
        self._form_vars["x"] = x_var
        tk.Entry(row, textvariable=x_var, width=8,
                 bg=BG_SECONDARY, fg=TEXT_COLOR, insertbackground=TEXT_COLOR,
                 font=FONT_MAIN, relief="flat", bd=0).pack(side="left", ipady=4, padx=(0, 10))

        tk.Label(row, text="Y", font=FONT_SMALL, bg=BG_PRIMARY,
                 fg=TEXT_DIM, width=4).pack(side="left")
        y_var = tk.StringVar(value=self._edit_val("y", "0"))
        self._form_vars["y"] = y_var
        tk.Entry(row, textvariable=y_var, width=8,
                 bg=BG_SECONDARY, fg=TEXT_COLOR, insertbackground=TEXT_COLOR,
                 font=FONT_MAIN, relief="flat", bd=0).pack(side="left", ipady=4)

        pick_btn = tk.Button(
            self._form_frame, text="🎯  Pick from screen", font=FONT_MAIN,
            bg=BG_SECONDARY, fg=TEXT_COLOR, activebackground=ACCENT,
            activeforeground=TEXT_COLOR, relief="flat", bd=0, cursor="hand2",
            command=lambda: self._pick_position(x_var, y_var),
        )
        pick_btn.pack(fill="x", pady=(8, 0), ipady=4)

        # Pre‑fill button type
        btn_var = tk.StringVar(value=self._edit_val(
            "button", button_map.get(aid, "left")))
        self._form_vars["button"] = btn_var

        if aid == "double_click":
            clicks_var = tk.StringVar(value=self._edit_val("clicks", "2"))
            self._form_vars["clicks"] = clicks_var

    def _form_scroll(self, aid: str):
        self._add_label("X position")
        self._add_entry("x", "0")
        self._add_label("Y position")
        self._add_entry("y", "0")
        direction = 1 if "up" in aid else -1
        self._add_label("Scroll amount (ticks)")
        default_amount = self._edit_val("amount", "3")
        self._add_spinbox("amount", from_=1, to=100, increment=1,
                          default=default_amount)
        # Store direction implicitly
        dir_var = tk.StringVar(value=str(direction))
        self._form_vars["direction"] = dir_var

    def _form_type_text(self, _aid: str):
        self._add_label("Text to type")
        self._add_text("text", height=5,
                       default=self._edit_val("text", ""))
        self._add_label("Typing delay between chars (seconds)")
        self._add_spinbox("char_delay", from_=0, to=2, increment=0.01,
                          default="0.02")

    def _form_key_press(self, _aid: str):
        self._add_label("Key (click the field then press a key)")
        key_var = tk.StringVar(value=self._edit_val("key", ""))
        self._form_vars["key"] = key_var
        entry = tk.Entry(
            self._form_frame, textvariable=key_var,
            bg=BG_SECONDARY, fg=TEXT_COLOR, insertbackground=TEXT_COLOR,
            font=FONT_MAIN, relief="flat", bd=0, state="readonly",
            readonlybackground=BG_SECONDARY,
        )
        entry.pack(fill="x", ipady=4, pady=(2, 0))
        self._form_widgets["key"] = entry

        # Capture next key press
        def _capture(event):
            name = event.keysym
            key_var.set(name)
            return "break"

        entry.bind("<Key>", _capture)
        entry.bind("<FocusIn>", lambda e: entry.configure(
            readonlybackground=ACCENT))
        entry.bind("<FocusOut>", lambda e: entry.configure(
            readonlybackground=BG_SECONDARY))

        hint = tk.Label(self._form_frame,
                        text="Click the field above, then press the desired key.",
                        font=FONT_SMALL, bg=BG_PRIMARY, fg=TEXT_DIM, anchor="w")
        hint.pack(fill="x", pady=(4, 0))

    def _form_key_combo(self, _aid: str):
        self._add_label("Key combination (e.g. Ctrl+C)")
        self._add_entry("combo", self._edit_val("combo", ""))

        hint = tk.Label(
            self._form_frame,
            text="Use + to separate keys:  Ctrl+Shift+S, Alt+F4, etc.",
            font=FONT_SMALL, bg=BG_PRIMARY, fg=TEXT_DIM, anchor="w",
            wraplength=280,
        )
        hint.pack(fill="x", pady=(4, 0))

    def _form_wait(self, _aid: str):
        self._add_label("Seconds to wait")
        self._add_spinbox("seconds", from_=0, to=3600, increment=0.1,
                          default=self._edit_val("seconds", "1.0"))

    def _form_wait_screen(self, _aid: str):
        self._add_label("Timeout (seconds)")
        self._add_spinbox("timeout", from_=1, to=300, increment=1,
                          default=self._edit_val("timeout", "30"))
        self._add_label("Region (x, y, w, h) — leave blank for full screen")
        self._add_entry("region", self._edit_val("region", ""))

    def _form_repeat(self, _aid: str):
        self._add_label("Number of iterations (0 = infinite)")
        self._add_spinbox("iterations", from_=0, to=999999, increment=1,
                          default=self._edit_val("iterations", "1"))

    def _form_find_image(self, _aid: str):
        self._add_label("Image file")
        row = tk.Frame(self._form_frame, bg=BG_PRIMARY)
        row.pack(fill="x", pady=(2, 0))
        img_var = tk.StringVar(value=self._edit_val("image_path", ""))
        self._form_vars["image_path"] = img_var
        tk.Entry(row, textvariable=img_var,
                 bg=BG_SECONDARY, fg=TEXT_COLOR, insertbackground=TEXT_COLOR,
                 font=FONT_MAIN, relief="flat", bd=0).pack(
            side="left", fill="x", expand=True, ipady=4)
        tk.Button(row, text="Browse…", font=FONT_SMALL,
                  bg=BG_SECONDARY, fg=TEXT_COLOR, activebackground=ACCENT,
                  relief="flat", bd=0, cursor="hand2",
                  command=lambda: img_var.set(
                      filedialog.askopenfilename(
                          filetypes=[("Images", "*.png *.jpg *.bmp")],
                          parent=self) or img_var.get())
                  ).pack(side="right", padx=(4, 0), ipady=2)

        self._add_label("Confidence threshold (0–1)")
        self._add_spinbox("confidence", from_=0, to=1, increment=0.05,
                          default=self._edit_val("confidence", "0.8"))

    def _form_find_text(self, _aid: str):
        self._add_label("Text to find (OCR)")
        self._add_entry("search_text", self._edit_val("search_text", ""))
        self._add_label("Timeout (seconds)")
        self._add_spinbox("timeout", from_=1, to=300, increment=1,
                          default=self._edit_val("timeout", "30"))

    def _form_run_app(self, _aid: str):
        self._add_label("Application path")
        row = tk.Frame(self._form_frame, bg=BG_PRIMARY)
        row.pack(fill="x", pady=(2, 0))
        path_var = tk.StringVar(value=self._edit_val("path", ""))
        self._form_vars["path"] = path_var
        tk.Entry(row, textvariable=path_var,
                 bg=BG_SECONDARY, fg=TEXT_COLOR, insertbackground=TEXT_COLOR,
                 font=FONT_MAIN, relief="flat", bd=0).pack(
            side="left", fill="x", expand=True, ipady=4)
        tk.Button(row, text="Browse…", font=FONT_SMALL,
                  bg=BG_SECONDARY, fg=TEXT_COLOR, activebackground=ACCENT,
                  relief="flat", bd=0, cursor="hand2",
                  command=lambda: path_var.set(
                      filedialog.askopenfilename(parent=self) or path_var.get())
                  ).pack(side="right", padx=(4, 0), ipady=2)

        self._add_label("Arguments")
        self._add_entry("args", self._edit_val("args", ""))

        self._add_label("Working directory (optional)")
        self._add_entry("cwd", self._edit_val("cwd", ""))

    def _form_save_variable(self, _aid: str):
        self._add_label("Variable name")
        self._add_entry("var_name", self._edit_val("var_name", ""))
        self._add_label("Value")
        self._add_entry("var_value", self._edit_val("var_value", ""))

    def _form_window_focus(self, _aid: str):
        self._add_label("Window title (substring match)")
        self._add_entry("window_title", self._edit_val("window_title", ""))

    # ---- screen picker helper ------------------------------------------
    def _pick_position(self, x_var: tk.StringVar, y_var: tk.StringVar):
        """Use the CoordinatePicker overlay to capture screen coordinates."""
        coords = CoordinatePicker.pick(self)
        if coords:
            x_var.set(str(coords[0]))
            y_var.set(str(coords[1]))

    # ===================================================================
    # Bottom buttons
    # ===================================================================
    def _build_buttons(self):
        bar = tk.Frame(self._right, bg=BG_PRIMARY)
        bar.pack(fill="x", side="bottom", pady=(0, 10), padx=10)

        confirm_text = "Save Changes" if self._is_edit else "Add Action"

        cancel_btn = tk.Button(
            bar, text="Cancel", font=FONT_MAIN,
            bg=BG_SECONDARY, fg=TEXT_COLOR, activebackground=BORDER_COLOR,
            activeforeground=TEXT_COLOR, relief="flat", bd=0, cursor="hand2",
            width=12, command=self._on_cancel,
        )
        cancel_btn.pack(side="right", ipady=6, padx=(6, 0))

        confirm_btn = tk.Button(
            bar, text=confirm_text, font=FONT_BOLD,
            bg=ACCENT, fg=TEXT_COLOR, activebackground=ACCENT_HOVER,
            activeforeground=TEXT_COLOR, relief="flat", bd=0, cursor="hand2",
            width=14, command=self._on_confirm,
        )
        confirm_btn.pack(side="right", ipady=6)

    # ===================================================================
    # Confirm / cancel
    # ===================================================================
    def _on_confirm(self):
        if not self._selected_id:
            self.bell()
            return

        result: dict = {"type": self._selected_id}

        # Gather all StringVar / IntVar / DoubleVar values
        for key, var in self._form_vars.items():
            result[key] = var.get()

        # Gather Text widget values (they aren't in _form_vars)
        for key, widget in self._form_widgets.items():
            if isinstance(widget, tk.Text):
                result[key] = widget.get("1.0", "end-1c")

        # Normalise numeric strings where appropriate
        for num_key in ("x", "y", "seconds", "timeout", "amount",
                        "duration", "confidence", "iterations",
                        "char_delay", "clicks"):
            if num_key in result:
                try:
                    result[num_key] = float(result[num_key])
                    if result[num_key] == int(result[num_key]):
                        result[num_key] = int(result[num_key])
                except (ValueError, TypeError):
                    pass

        # Strip empty optional fields
        result = {k: v for k, v in result.items() if v != "" and v is not None}

        self.result = result
        self.destroy()

    def _on_cancel(self):
        self.result = None
        self.destroy()

    # ===================================================================
    # Pre‑select when editing an existing action
    # ===================================================================
    def _preselect(self, action: dict):
        aid = action.get("type", "")
        if aid in _ACTION_META:
            self._on_type_select(aid)


# -----------------------------------------------------------------------
# Convenience wrapper — call from MacroRecorderWindow
# -----------------------------------------------------------------------
def open_action_editor(
    parent: tk.Misc,
    action: Optional[dict] = None,
) -> Optional[dict]:
    """Open the action editor and return the resulting dict (or None)."""
    title = "Edit Action" if action else "Add Action"
    dlg = ActionEditorDialog(parent, action=action, title=title)
    dlg.wait_window()
    return dlg.result


# -----------------------------------------------------------------------
# Standalone test
# -----------------------------------------------------------------------
if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()

    # Test: open as "Add" dialog
    result = open_action_editor(root)
    if result:
        import pprint
        pprint.pprint(result)
    else:
        print("Cancelled.")

    root.destroy()
