import tkinter as tk
from tkinter import ttk
import customtkinter as ctk

from ui.theme import BG_PRIMARY, BG_SECONDARY, ACCENT, TEXT_COLOR, TEXT_DIM
from features.scheduler import MacroScheduler

class SchedulePanel(ctk.CTkFrame):
    """UI Panel for managing scheduled macros."""

    def __init__(self, master, scheduler: MacroScheduler, macro_list: list[str], **kwargs):
        super().__init__(master, fg_color=BG_PRIMARY, **kwargs)
        self.scheduler = scheduler
        self.macro_list = macro_list

        # Top Bar
        top_bar = ctk.CTkFrame(self, fg_color=BG_SECONDARY, corner_radius=8)
        top_bar.pack(fill="x", pady=(0, 10))

        title = ctk.CTkLabel(top_bar, text="⏰ Scheduled Tasks", font=("Segoe UI", 16, "bold"), text_color=TEXT_COLOR)
        title.pack(side="left", padx=15, pady=10)

        # Form for adding a new task
        form_frame = ctk.CTkFrame(self, fg_color=BG_SECONDARY, corner_radius=8)
        form_frame.pack(fill="x", pady=(0, 15), ipadx=10, ipady=10)

        ctk.CTkLabel(form_frame, text="Macro:").grid(row=0, column=0, padx=10, pady=10, sticky="e")
        self.macro_dropdown = ctk.CTkOptionMenu(form_frame, values=self.macro_list or ["No macros found"])
        self.macro_dropdown.grid(row=0, column=1, padx=10, pady=10)

        ctk.CTkLabel(form_frame, text="Time (HH:MM):").grid(row=0, column=2, padx=10, pady=10, sticky="e")
        
        self.hour_entry = ctk.CTkEntry(form_frame, width=50, placeholder_text="00")
        self.hour_entry.grid(row=0, column=3, padx=2)
        
        ctk.CTkLabel(form_frame, text=":").grid(row=0, column=4)
        
        self.minute_entry = ctk.CTkEntry(form_frame, width=50, placeholder_text="00")
        self.minute_entry.grid(row=0, column=5, padx=2)

        add_btn = ctk.CTkButton(form_frame, text="+ Add Schedule", command=self._on_add, fg_color=ACCENT)
        add_btn.grid(row=0, column=6, padx=20)

        # Task List
        list_frame = ctk.CTkFrame(self, fg_color=BG_SECONDARY, corner_radius=8)
        list_frame.pack(fill="both", expand=True)

        columns = ("macro", "time", "status")
        self.tree = ttk.Treeview(list_frame, columns=columns, show="headings", style="Dark.Treeview", height=15)
        self.tree.heading("macro", text="Macro Name")
        self.tree.heading("time", text="Scheduled Time")
        self.tree.heading("status", text="Status")
        
        self.tree.column("macro", width=250)
        self.tree.column("time", width=100, anchor="center")
        self.tree.column("status", width=100, anchor="center")

        self.tree.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Bottom controls
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", pady=10)
        
        ctk.CTkButton(btn_frame, text="Delete Selected", command=self._on_delete, fg_color="#e74c3c", hover_color="#c0392b").pack(side="right", padx=10)
        ctk.CTkButton(btn_frame, text="Toggle Status", command=self._on_toggle, fg_color="#3498db").pack(side="right")

        self._refresh_list()

    def update_macro_list(self, new_list: list[str]):
        """Update the dropdown when new macros are saved."""
        self.macro_list = new_list
        self.macro_dropdown.configure(values=self.macro_list or ["No macros found"])
        if self.macro_list:
            self.macro_dropdown.set(self.macro_list[0])

    def _refresh_list(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        for idx, task in enumerate(self.scheduler.tasks):
            time_str = f"{task.hour:02d}:{task.minute:02d}"
            status_str = "Active" if task.enabled else "Disabled"
            self.tree.insert("", "end", iid=str(idx), values=(task.macro_name, time_str, status_str))

    def _on_add(self):
        macro = self.macro_dropdown.get()
        if not macro or macro == "No macros found":
            return
            
        try:
            h = int(self.hour_entry.get())
            m = int(self.minute_entry.get())
            if 0 <= h <= 23 and 0 <= m <= 59:
                self.scheduler.add_task(macro, h, m)
                self._refresh_list()
                self.hour_entry.delete(0, tk.END)
                self.minute_entry.delete(0, tk.END)
        except ValueError:
            pass # Invalid input

    def _on_delete(self):
        selected = self.tree.selection()
        if not selected:
            return
        idx = int(selected[0])
        self.scheduler.remove_task(idx)
        self._refresh_list()
        
    def _on_toggle(self):
        selected = self.tree.selection()
        if not selected:
            return
        idx = int(selected[0])
        current_status = self.scheduler.tasks[idx].enabled
        self.scheduler.toggle_task(idx, not current_status)
        self._refresh_list()
