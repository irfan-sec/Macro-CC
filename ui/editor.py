"""
Tkinter macro editor with dark theme.

Lists saved macros, allows renaming and deleting.
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from storage.macro_store import MacroStore


class MacroEditor:
    """
    Tkinter macro editor.

    Features:
    - List all saved macros with stats
    - Rename / delete macros
    - Dark themed UI
    """

    def __init__(self, store: MacroStore):
        self.store = store
        self.root = None
        self._selected_macro = None

    def run(self):
        """Launch editor window — blocks until closed."""
        self.root = tk.Tk()
        self.root.title("🖱️ Mouse Macro Editor")
        self.root.geometry("700x500")
        self.root.resizable(True, True)
        self.root.configure(bg="#1e1e2e")

        self._build_ui()
        self._refresh_list()
        self.root.mainloop()

    def run_as_toplevel(self, parent):
        """Launch as a Toplevel window (avoids creating a second Tk instance)."""
        self.root = tk.Toplevel(parent)
        self.root.title("🖱️ Mouse Macro Editor")
        self.root.geometry("700x500")
        self.root.resizable(True, True)
        self.root.configure(bg="#1e1e2e")

        self._build_ui()
        self._refresh_list()
        self.root.grab_set()
        self.root.focus_force()

    def _build_ui(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview",
            background="#2a2a3e", foreground="white",
            fieldbackground="#2a2a3e", rowheight=28)
        style.configure("Treeview.Heading",
            background="#3a3a5e", foreground="white")

        # ── Header ──
        header = tk.Label(self.root, text="🖱️  Macro Library",
            font=("Segoe UI", 16, "bold"),
            bg="#1e1e2e", fg="white", pady=12)
        header.pack(fill=tk.X)

        # ── Macro List ──
        list_frame = tk.Frame(self.root, bg="#1e1e2e")
        list_frame.pack(fill=tk.BOTH, expand=True, padx=12)

        columns = ("name", "events", "duration", "saved")
        self.tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=12)

        self.tree.heading("name",     text="Macro Name")
        self.tree.heading("events",   text="Events")
        self.tree.heading("duration", text="Duration")
        self.tree.heading("saved",    text="Saved At")

        self.tree.column("name",     width=200)
        self.tree.column("events",   width=80,  anchor="center")
        self.tree.column("duration", width=100, anchor="center")
        self.tree.column("saved",    width=180)

        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        # ── Buttons ──
        btn_frame = tk.Frame(self.root, bg="#1e1e2e", pady=8)
        btn_frame.pack(fill=tk.X, padx=12)

        buttons = [
            ("🔄 Refresh",  self._refresh_list, "#3a3a5e"),
            ("✏️  Rename",  self._rename_macro,  "#3a6e5e"),
            ("🗑️  Delete",  self._delete_macro,  "#6e3a3a"),
        ]
        for label, cmd, color in buttons:
            tk.Button(btn_frame, text=label, command=cmd,
                bg=color, fg="white", relief="flat",
                padx=14, pady=6, cursor="hand2",
                font=("Segoe UI", 10)
            ).pack(side=tk.LEFT, padx=4)

        # ── Status Bar ──
        self.status_var = tk.StringVar(value="Select a macro to see options")
        status = tk.Label(self.root, textvariable=self.status_var,
            bg="#13131f", fg="#888", font=("Segoe UI", 9), pady=5)
        status.pack(fill=tk.X, side=tk.BOTTOM)

    def _refresh_list(self):
        """Reload macro list from disk."""
        for row in self.tree.get_children():
            self.tree.delete(row)

        macros = self.store.list_all()
        for m in macros:
            self.tree.insert("", "end", values=(
                m["name"],
                m["event_count"],
                f"{m['duration_seconds']:.1f}s",
                m["saved_at"][:19].replace("T", " "),
            ))

        self.status_var.set(f"{len(macros)} macro(s) found")

    def _on_select(self, event):
        selected = self.tree.selection()
        if selected:
            values = self.tree.item(selected[0])["values"]
            self._selected_macro = str(values[0])  # Ensure it's a string
            self.status_var.set(
                f"Selected: {values[0]}  |  {values[1]} events  |  {values[2]}"
            )
        else:
            self._selected_macro = None

    def _rename_macro(self):
        if not self._selected_macro:
            messagebox.showinfo("Rename", "Please select a macro first.",
                                parent=self.root)
            return

        new_name = simpledialog.askstring(
            "Rename Macro",
            f"Rename '{self._selected_macro}' to:",
            initialvalue=self._selected_macro,
            parent=self.root
        )
        if new_name and new_name != self._selected_macro:
            if self.store.rename(self._selected_macro, new_name):
                self._selected_macro = None
                self._refresh_list()
            else:
                messagebox.showerror("Error",
                                     f"Could not rename to '{new_name}'",
                                     parent=self.root)

    def _delete_macro(self):
        if not self._selected_macro:
            messagebox.showinfo("Delete", "Please select a macro first.",
                                parent=self.root)
            return

        confirm = messagebox.askyesno(
            "Delete Macro",
            f"Delete '{self._selected_macro}'?\nThis cannot be undone.",
            icon="warning",
            parent=self.root
        )
        if confirm:
            if self.store.delete(self._selected_macro):
                self._selected_macro = None
                self._refresh_list()
            else:
                messagebox.showerror("Error",
                                     f"Could not delete '{self._selected_macro}'.",
                                     parent=self.root)
