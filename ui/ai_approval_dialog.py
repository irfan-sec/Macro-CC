import tkinter as tk
from tkinter import ttk, messagebox
import customtkinter as ctk
import json
from core.event_model import SystemEvent, KeyboardEvent, MouseEvent

class AIApprovalDialog(ctk.CTkToplevel):
    def __init__(self, parent, events: list):
        super().__init__(parent)
        self.title("AI Macro Generation - Approval")
        self.geometry("700x500")
        self.transient(parent)
        self.grab_set()
        
        self.events = events
        self.approved_events = None

        # Title
        title = ctk.CTkLabel(self, text="Review Generated Macro Actions", font=ctk.CTkFont(size=16, weight="bold"))
        title.pack(pady=10)

        # Main frame
        frame = ctk.CTkFrame(self)
        frame.pack(fill="both", expand=True, padx=10, pady=5)

        # Treeview to display events (CustomTkinter doesn't have a native Treeview, so we use ttk.Treeview)
        columns = ("#", "Type", "Action", "Value")
        self.tree = ttk.Treeview(frame, columns=columns, show="headings", height=15)
        self.tree.heading("#", text="#")
        self.tree.heading("Type", text="Type")
        self.tree.heading("Action", text="Action")
        self.tree.heading("Value", text="Value")
        
        self.tree.column("#", width=40, anchor="center")
        self.tree.column("Type", width=120)
        self.tree.column("Action", width=120)
        self.tree.column("Value", width=350)
        
        # Scrollbar
        scroll = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        
        self.tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        
        # Populate
        self._populate_tree()

        # Buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=10, pady=10)
        
        approve_btn = ctk.CTkButton(btn_frame, text="Approve & Insert", command=self._on_approve, fg_color="#2ecc71", hover_color="#27ae60")
        approve_btn.pack(side="right", padx=5)
        
        cancel_btn = ctk.CTkButton(btn_frame, text="Cancel", command=self.destroy, fg_color="#e74c3c", hover_color="#c0392b")
        cancel_btn.pack(side="right", padx=5)

    def _populate_tree(self):
        self.tree.delete(*self.tree.get_children())
        for i, ev in enumerate(self.events):
            if isinstance(ev, SystemEvent):
                val = f"{ev.value} ({ev.comment})" if ev.comment else ev.value
                self.tree.insert("", "end", values=(i+1, "System", ev.action, val))
            elif isinstance(ev, KeyboardEvent):
                self.tree.insert("", "end", values=(i+1, "Keyboard", ev.type, ev.key))
            elif isinstance(ev, MouseEvent):
                val = f"x:{ev.x}, y:{ev.y}"
                self.tree.insert("", "end", values=(i+1, "Mouse", ev.type, val))

    def _on_approve(self):
        self.approved_events = self.events
        self.destroy()

def open_ai_approval(parent, events: list) -> list:
    dialog = AIApprovalDialog(parent, events)
    parent.wait_window(dialog)
    return dialog.approved_events
