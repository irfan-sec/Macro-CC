"""
Macro Recorder Pro — Professional dark-themed tkinter GUI.
Replaces any previous tkinter UI with a polished, enterprise-style window.
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
import customtkinter as ctk
import json
import os
import sys
import time
from pathlib import Path

# Ensure the project root is on sys.path so `ui.` imports work
# regardless of whether we're launched as `python ui/main_window.py`
# or imported as a package.
_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from ui.theme import (
    BG_PRIMARY, BG_SECONDARY, ACCENT, ACCENT_HOVER,
    TEXT_COLOR, TEXT_DIM, BORDER_COLOR, SUCCESS, WARNING,
    ROW_ALT_A, ROW_ALT_B,
    FONT_MAIN, FONT_SMALL, FONT_BOLD, FONT_HEADER, FONT_MONO,
)
from ui.action_editor import open_action_editor
from ui.search_replace import open_search_replace
from ui.speed_control import open_speed_dialog
from ui.recording_overlay import RecordingOverlay
from ui.network_dialog import open_network_dialog
from ui.ai_approval_dialog import open_ai_approval
from ui.ai_settings_dialog import open_ai_settings, load_ai_settings
from ui.sidebar import Sidebar
from ui.log_console import LogConsole
from ui.schedule_panel import SchedulePanel
from ui.ai_chat_panel import AIChatPanel
from features.ai_agent import AIAgent
from features.scheduler import MacroScheduler
import config

# Toolbar button definitions — (emoji, label, callback‑method‑name)
TOOLBAR_GROUPS: list[list[tuple[str, str, str]]] = [
    [
        ("▶",  "Play",    "_on_play"),
        ("⏺",  "Record",  "_on_record"),
        ("⏹",  "Stop",    "_on_stop"),
    ],
    [
        ("🖱", "Mouse",   "_on_insert_mouse"),
        ("⌨",  "Text/Key","_on_insert_key"),
        ("⏱",  "Wait",    "_on_insert_wait"),
        ("🖼", "Image",   "_on_insert_image"),
    ],
    [
        ("✏",  "Edit",    "_on_edit_action"),
        ("🗑", "Delete",  "_on_delete_action"),
        ("🔍", "Search",  "_on_search_actions"),
        ("🌐", "Network", "_on_network"),
    ],
]


class DarkButton(tk.Canvas):
    """A rounded, hover‑aware button drawn on a Canvas with high‑contrast styling."""

    def __init__(
        self,
        parent,
        text: str = "",
        emoji: str = "",
        width: int = 68,
        height: int = 58,
        command=None,
        **kw,
    ):
        super().__init__(
            parent,
            width=width,
            height=height,
            bg=BG_PRIMARY,
            highlightthickness=0,
            **kw,
        )
        self._command = command
        self._width = width
        self._height = height
        self._bg_normal = "#253255"       # clearly lighter than toolbar bg
        self._bg_hover = ACCENT
        self._bg_press = ACCENT_HOVER
        self._border_normal = "#3a4a6e"   # visible border
        self._border_hover = "#ff8fa3"
        self._current_bg = self._bg_normal
        self._emoji = emoji
        self._text = text

        self._draw(self._bg_normal, self._border_normal)

        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_click)
        # Also bind on all canvas items so clicks on emoji/text work
        self.tag_bind("all", "<ButtonRelease-1>", self._on_click)
        self.tag_bind("all", "<ButtonPress-1>", self._on_press)

    # -- drawing helpers --------------------------------------------------
    def _rounded_rect(self, x1, y1, x2, y2, r, **kw):
        points = [
            x1 + r, y1, x2 - r, y1,
            x2, y1, x2, y1 + r,
            x2, y2 - r, x2, y2,
            x2 - r, y2, x1 + r, y2,
            x1, y2, x1, y2 - r,
            x1, y1 + r, x1, y1,
        ]
        return self.create_polygon(points, smooth=True, **kw)

    def _draw(self, bg, border=None):
        if border is None:
            border = self._border_normal
        self.delete("all")
        self._rounded_rect(2, 2, self._width - 2, self._height - 2, 10,
                           fill=bg, outline=border, width=2)
        if self._emoji:
            self.create_text(
                self._width // 2, self._height // 2 - 9,
                text=self._emoji, font=("Segoe UI Emoji", 15),
                fill=TEXT_COLOR,
            )
        if self._text:
            self.create_text(
                self._width // 2, self._height - 11,
                text=self._text, font=("Segoe UI", 9), fill="#ccd6f6",
            )
        # Re-bind click on canvas items after redraw
        self.tag_bind("all", "<ButtonRelease-1>", self._on_click)
        self.tag_bind("all", "<ButtonPress-1>", self._on_press)

    # -- event handlers ---------------------------------------------------
    def _on_enter(self, _e):
        self._draw(self._bg_hover, self._border_hover)

    def _on_leave(self, _e):
        self._draw(self._bg_normal, self._border_normal)

    def _on_press(self, _e):
        self._draw(self._bg_press, self._border_hover)

    def _on_click(self, _e):
        self._draw(self._bg_hover, self._border_hover)
        if self._command:
            self._command()


class MacroRecorderWindow(ctk.CTk):
    """Main application window for Macro Recorder Pro."""

    def __init__(self, app=None):
        super().__init__()
        # Keep a reference to the App controller from main.py
        self._app = app

        # -- window basics ------------------------------------------------
        self.title("⚡ Macro Recorder Pro v2.0")
        self.geometry("1100x700")
        self.minsize(900, 600)
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        self.configure(bg=BG_PRIMARY)
        load_ai_settings()
        self.ai_agent = AIAgent()

        # Window icon (works for both frozen .exe and dev mode)
        _icon_path = os.path.join(
            os.path.dirname(sys.executable) if getattr(sys, 'frozen', False)
            else os.path.dirname(os.path.abspath(__file__)),
            os.pardir, "assets", "icon.ico",
        )
        if os.path.isfile(_icon_path):
            try:
                self.iconbitmap(_icon_path)
            except Exception:
                pass
        self.option_add("*TCombobox*Listbox.background", BG_SECONDARY)
        self.option_add("*TCombobox*Listbox.foreground", TEXT_COLOR)

        # State
        self._status = "Ready"
        self._event_count = 0
        self._duration = 0.0
        self._speed = 1.0
        self._show_toolbar = tk.BooleanVar(value=True)
        self._show_statusbar = tk.BooleanVar(value=True)
        self._macros: list[dict] = []  # [{name, events, duration}, ...]
        self._rec_overlay: RecordingOverlay | None = None
        self._rec_update_id = None
        self._vars_visible = tk.BooleanVar(value=False)
        self._current_macro_name = "macro1"
        self._loaded_events: list[dict] = []  # full event dicts for current display
        self._undo_stack = []
        self._redo_stack = []

        # -- Engine (use app's components, or create standalone) ----------
        if self._app:
            self._recorder = self._app.recorder
            self._player = self._app.player
            self._store = self._app.store
            self._current_macro_name = getattr(
                self._app, "current_macro_name", "macro1"
            )
        else:
            from core.recorder import Recorder
            from core.player import Player
            from storage.macro_store import MacroStore
            self._recorder = Recorder()
            self._player = Player()
            self._store = MacroStore(config.MACROS_DIR)
            
        # -- Scheduler ----------------------------------------------------
        self._scheduler = MacroScheduler(self._store, self._player)
        self._scheduler.start()

        # -- Tray icon (only create one if we don't have an app's tray) ----
        self._tray = None
        if self._app and hasattr(self._app, 'tray'):
            self._tray = self._app.tray  # reuse the App's tray
        else:
            try:
                from ui.tray_icon import TrayIcon
                self._tray = TrayIcon(self._make_tray_app_proxy())
                self._tray.start()
            except Exception as exc:
                print(f"[MainWindow] Tray icon failed to start: {exc}")

        # -- configure ttk styles ----------------------------------------
        self._setup_styles()

        # -- build UI layers with sidebar layout -------------------------
        self._build_menubar()

        # Root layout: sidebar on left, content area on right
        self._root_container = tk.Frame(self, bg=BG_PRIMARY)
        self._root_container.pack(fill="both", expand=True)

        # Sidebar
        self._sidebar = Sidebar(self._root_container, on_navigate=self._on_sidebar_navigate)
        self._sidebar.pack(side="left", fill="y")

        # Right content area (toolbar + AI bar + main + console + status)
        self._content_area = tk.Frame(self._root_container, bg=BG_PRIMARY)
        self._content_area.pack(side="left", fill="both", expand=True)

        self._toolbar_frame = self._build_toolbar()
        self._ai_frame = self._build_ai_command_bar()
        self._build_main_area()
        
        # Schedule Panel (hidden initially)
        self._schedule_panel = SchedulePanel(self._content_area, self._scheduler, [])

        # AI Chat Panel (hidden initially)
        self._ai_chat_panel = AIChatPanel(self._content_area, self)

        # Log console (bottom)
        self._log_console = LogConsole(self._content_area)
        self._log_console.pack(fill="x", side="bottom", before=self._status_bar if hasattr(self, '_status_bar') else None)

        self._status_bar = self._build_status_bar()

        # Capture stdout to log console
        self._log_console.capture_stdout()

        # -- populate macro library with any saved files ------------------
        self._refresh_macro_library()
        self._schedule_panel.update_macro_list([m["name"] for m in self._macros])

        # -- bind global shortcuts ---------------------------------------
        self.bind_all("<Control-n>", lambda e: self._on_new_macro())
        self.bind_all("<Control-o>", lambda e: self._on_open())
        self.bind_all("<Control-s>", lambda e: self._on_save())
        self.bind_all("<Control-Shift-S>", lambda e: self._on_save_as())
        self.bind_all("<Control-h>", lambda e: self._on_search_actions())

        # -- start network status auto-refresh --
        self.after(500, self._start_net_status_timer)

        # Log startup
        self._log_console.log(f"⚡ {config.APP_NAME} v{config.APP_VERSION} started", 'success')
        self._log_console.log("AI Engine ready • Sidebar navigation enabled", 'ai')

        # -- Onboarding Wizard --
        from ui.onboarding import show_onboarding_if_needed
        self.after(500, lambda: show_onboarding_if_needed(self))

    # ===================================================================
    # Sidebar Navigation
    # ===================================================================
    def _on_sidebar_navigate(self, page: str):
        """Handle sidebar navigation clicks."""
        # Hide all optional panels first
        if hasattr(self, '_schedule_panel'): self._schedule_panel.pack_forget()
        if hasattr(self, '_ai_chat_panel'): self._ai_chat_panel.pack_forget()
        self._toolbar_frame.pack_forget()
        self._ai_frame.pack_forget()
        self._main_container.pack_forget()
        
        if page in ("Home", "Macros"):
            # Show main editor panels
            self._toolbar_frame.pack(fill="x", side="top")
            self._ai_frame.pack(fill="x", side="top", padx=10, pady=(5, 5))
            self._main_container.pack(fill="both", expand=True, padx=4, pady=(0, 4))
            
            if page == "Home":
                self._log_console.log("📍 Navigated to Home", 'info')
            elif page == "Macros":
                self._log_console.log("📁 Navigated to Macro Library", 'info')
                self._macro_listbox.focus_set()
                
        elif page == "AI Assistant":
            self._log_console.log("✨ AI Assistant full panel activated", 'ai')
            self._ai_chat_panel.pack(fill="both", expand=True, padx=10, pady=10)
            
        elif page == "Scheduler":
            self._log_console.log("⏰ Navigated to Scheduler", 'info')
            self._schedule_panel.update_macro_list([m["name"] for m in self._macros])
            self._schedule_panel.pack(fill="both", expand=True, padx=10, pady=10)
            
        elif page == "Network":
            # Just open the modal over whatever is open
            self._on_network()
            
        elif page == "Settings":
            open_ai_settings(self)

    # ===================================================================
    # Styles
    # ===================================================================
    def _setup_styles(self):
        style = ttk.Style(self)
        style.theme_use("clam")

        # Treeview
        style.configure(
            "Dark.Treeview",
            background=BG_PRIMARY,
            foreground=TEXT_COLOR,
            fieldbackground=BG_PRIMARY,
            borderwidth=0,
            font=FONT_MAIN,
            rowheight=28,
        )
        style.map(
            "Dark.Treeview",
            background=[("selected", ACCENT)],
            foreground=[("selected", TEXT_COLOR)],
        )
        style.configure(
            "Dark.Treeview.Heading",
            background=BG_SECONDARY,
            foreground=TEXT_DIM,
            font=FONT_BOLD,
            borderwidth=0,
        )
        style.map(
            "Dark.Treeview.Heading",
            background=[("active", ACCENT)],
        )

        # Scrollbar
        style.configure(
            "Dark.Vertical.TScrollbar",
            troughcolor=BG_PRIMARY,
            background=BG_SECONDARY,
            arrowcolor=TEXT_DIM,
            borderwidth=0,
        )
        style.map(
            "Dark.Vertical.TScrollbar",
            background=[("active", ACCENT)],
        )

        # Separator
        style.configure("Dark.TSeparator", background=BORDER_COLOR)

    # ===================================================================
    # Menu bar
    # ===================================================================
    def _build_menubar(self):
        menubar = tk.Menu(self, bg=BG_SECONDARY, fg=TEXT_COLOR,
                          activebackground=ACCENT, activeforeground=TEXT_COLOR,
                          relief="flat", bd=0)

        # -- File ---------------------------------------------------------
        file_menu = tk.Menu(menubar, tearoff=0, bg=BG_SECONDARY,
                            fg=TEXT_COLOR, activebackground=ACCENT,
                            activeforeground=TEXT_COLOR)
        file_menu.add_command(label="New Macro      Ctrl+N",  command=self._on_new_macro)
        file_menu.add_command(label="Open…          Ctrl+O",  command=self._on_open)
        file_menu.add_separator()
        file_menu.add_command(label="Save           Ctrl+S",  command=self._on_save)
        file_menu.add_command(label="Save As…       Ctrl+Shift+S", command=self._on_save_as)
        file_menu.add_separator()
        file_menu.add_command(label="Import…", command=self._on_import)
        file_menu.add_command(label="Export…", command=self._on_export)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self._on_exit)
        menubar.add_cascade(label="File", menu=file_menu)

        # -- Edit ---------------------------------------------------------
        edit_menu = tk.Menu(menubar, tearoff=0, bg=BG_SECONDARY,
                            fg=TEXT_COLOR, activebackground=ACCENT,
                            activeforeground=TEXT_COLOR)
        edit_menu.add_command(label="Undo           Ctrl+Z",  command=self._on_undo)
        edit_menu.add_command(label="Redo           Ctrl+Y",  command=self._on_redo)
        edit_menu.add_separator()
        edit_menu.add_command(label="Select All     Ctrl+A",  command=self._on_select_all)
        edit_menu.add_command(label="Delete Selected",        command=self._on_delete_action)
        edit_menu.add_separator()
        edit_menu.add_command(label="Search & Replace  Ctrl+H", command=self._on_search_actions)
        menubar.add_cascade(label="Edit", menu=edit_menu)

        # -- Playback -----------------------------------------------------
        play_menu = tk.Menu(menubar, tearoff=0, bg=BG_SECONDARY,
                            fg=TEXT_COLOR, activebackground=ACCENT,
                            activeforeground=TEXT_COLOR)
        play_menu.add_command(label="▶  Play",   command=self._on_play)
        play_menu.add_command(label="⏹  Stop",   command=self._on_stop)
        play_menu.add_separator()
        play_menu.add_command(label="⏺  Record", command=self._on_record)
        play_menu.add_command(label="⏸  Pause",  command=self._on_pause)
        play_menu.add_separator()
        play_menu.add_command(label="Speed…",    command=self._on_set_speed)
        menubar.add_cascade(label="Playback", menu=play_menu)

        # -- View ---------------------------------------------------------
        view_menu = tk.Menu(menubar, tearoff=0, bg=BG_SECONDARY,
                            fg=TEXT_COLOR, activebackground=ACCENT,
                            activeforeground=TEXT_COLOR)
        view_menu.add_checkbutton(label="Show Toolbar",
                                  variable=self._show_toolbar,
                                  command=self._toggle_toolbar)
        view_menu.add_checkbutton(label="Show Status Bar",
                                  variable=self._show_statusbar,
                                  command=self._toggle_statusbar)
        view_menu.add_separator()
        view_menu.add_checkbutton(label="Show Variables",
                                  variable=self._vars_visible,
                                  command=self._toggle_variables)
        view_menu.add_separator()
        view_menu.add_command(label="Zoom In   Ctrl++",  command=lambda: None)
        view_menu.add_command(label="Zoom Out  Ctrl+-",  command=lambda: None)
        menubar.add_cascade(label="View", menu=view_menu)

        # -- Help ---------------------------------------------------------
        help_menu = tk.Menu(menubar, tearoff=0, bg=BG_SECONDARY,
                            fg=TEXT_COLOR, activebackground=ACCENT,
                            activeforeground=TEXT_COLOR)
        help_menu.add_command(label="About",          command=self._on_about)
        help_menu.add_command(label="Documentation",  command=self._on_docs)
        menubar.add_cascade(label="Help", menu=help_menu)

        self.config(menu=menubar)

    # ===================================================================
    # Toolbar
    # ===================================================================
    def _build_toolbar(self) -> tk.Frame:
        parent = self._content_area
        frame = tk.Frame(parent, bg=BG_SECONDARY, height=44)
        frame.pack(fill="x", side="top")

        for gi, group in enumerate(TOOLBAR_GROUPS):
            for emoji, label, method_name in group:
                cb = getattr(self, method_name, None)
                btn = DarkButton(frame, text=label, emoji=emoji,
                                 command=cb)
                btn.pack(side="left", padx=2, pady=2)
            # separator between groups
            if gi < len(TOOLBAR_GROUPS) - 1:
                sep = tk.Frame(frame, width=2, bg=BORDER_COLOR)
                sep.pack(side="left", fill="y", padx=6, pady=6)

        # ── Loop control (right side of toolbar) ────────────
        loop_sep = tk.Frame(frame, width=2, bg=BORDER_COLOR)
        loop_sep.pack(side="left", fill="y", padx=6, pady=6)

        tk.Label(frame, text="🔁 Loops:", font=FONT_SMALL,
                 bg=BG_PRIMARY, fg=TEXT_DIM).pack(side="left", padx=(4, 2))

        self._loop_count = tk.IntVar(value=1)
        self._loop_spin = tk.Spinbox(
            frame, from_=1, to=9999, textvariable=self._loop_count,
            width=5, font=FONT_MAIN, bg=BG_SECONDARY, fg=TEXT_COLOR,
            buttonbackground=BG_SECONDARY, insertbackground=TEXT_COLOR,
            relief="flat", bd=0, highlightthickness=1,
            highlightbackground=BORDER_COLOR, highlightcolor=ACCENT,
        )
        self._loop_spin.pack(side="left", padx=2, ipady=2)

        self._inf_loop = tk.BooleanVar(value=False)
        self._inf_btn = tk.Checkbutton(
            frame, text="∞", variable=self._inf_loop,
            command=self._toggle_infinite,
            font=("Segoe UI", 14, "bold"), bg=BG_PRIMARY, fg=TEXT_DIM,
            activebackground=BG_PRIMARY, activeforeground=ACCENT,
            selectcolor=BG_SECONDARY, indicatoron=False,
            width=2, relief="flat", bd=0,
        )
        self._inf_btn.pack(side="left", padx=2)

        return frame

    def _toggle_infinite(self):
        if self._inf_loop.get():
            self._loop_spin.config(state="disabled")
            self._inf_btn.config(fg=ACCENT)
        else:
            self._loop_spin.config(state="normal")
            self._inf_btn.config(fg=TEXT_DIM)

    def get_loop_count(self) -> int:
        """Return current loop count (0 = infinite)."""
        if self._inf_loop.get():
            return 0
        return self._loop_count.get()

    # ===================================================================
    # AI Command Bar
    # ===================================================================
    def _build_ai_command_bar(self) -> ctk.CTkFrame:
        frame = ctk.CTkFrame(self._content_area, fg_color=BG_SECONDARY, corner_radius=8)
        frame.pack(fill="x", side="top", padx=10, pady=(5, 5))

        label = ctk.CTkLabel(frame, text="✨ AI Command:", font=ctk.CTkFont(size=14, weight="bold"), text_color="#2ecc71")
        label.pack(side="left", padx=10, pady=10)

        self.ai_input_var = tk.StringVar()
        entry = ctk.CTkEntry(frame, textvariable=self.ai_input_var, placeholder_text="e.g. Open Notepad and type Hello World", font=ctk.CTkFont(size=13), height=35)
        entry.pack(side="left", fill="x", expand=True, padx=(0, 10), pady=10)
        
        # Bind enter key
        entry.bind("<Return>", lambda e: self._on_ai_generate())

        btn = ctk.CTkButton(frame, text="Generate Macro", font=ctk.CTkFont(weight="bold"), 
                            fg_color="#e94560", hover_color="#ff6b81", height=35,
                            command=self._on_ai_generate)
        btn.pack(side="right", padx=(5, 10), pady=10)
        
        settings_btn = ctk.CTkButton(frame, text="⚙️", width=35, height=35,
                                     fg_color="#34495e", hover_color="#2c3e50",
                                     command=lambda: open_ai_settings(self))
        settings_btn.pack(side="right", padx=(10, 5), pady=10)

        return frame

    def _on_ai_generate(self):
        command = self.ai_input_var.get().strip()
        if not command:
            return
            
        try:
            self.config(cursor="wait")
            self.update()
            
            # Generate events
            events = self.ai_agent.generate_macro(command)
            
            if not events:
                messagebox.showinfo("AI Generate", "No events were generated.")
                return
                
            # Show approval dialog
            approved = open_ai_approval(self, events)
            
            if approved:
                self._push_undo_state()
                # Add to current macro or create new
                for ev in approved:
                    self._loaded_events.append(ev.to_dict())
                self._refresh_action_list()
                self._save_current_silently()
                
        except Exception as e:
            messagebox.showerror("AI Error", f"Failed to generate macro:\n{e}")
        finally:
            self.config(cursor="")
            self.ai_input_var.set("") # Clear input

    # ===================================================================
    # Main area — left (library) + right (action list)
    # ===================================================================
    def _build_main_area(self):
        container = tk.Frame(self._content_area, bg=BG_PRIMARY)
        container.pack(fill="both", expand=True, padx=4, pady=(0, 4))
        self._main_container = container

        # -- Left panel: macro library -----------------------------------
        left = tk.Frame(container, bg=BG_SECONDARY, width=260)
        left.pack(side="left", fill="y", padx=(0, 4))
        left.pack_propagate(False)

        header = tk.Label(left, text="📁 Macro Library", font=FONT_HEADER,
                          bg=BG_SECONDARY, fg=TEXT_COLOR, anchor="w")
        header.pack(fill="x", padx=10, pady=(10, 4))

        # Search box
        search_frame = tk.Frame(left, bg=BG_SECONDARY)
        search_frame.pack(fill="x", padx=10, pady=(0, 6))
        self._lib_search_var = tk.StringVar()
        self._lib_search_var.trace_add("write", self._on_lib_search)
        search_entry = tk.Entry(
            search_frame, textvariable=self._lib_search_var,
            bg=BG_PRIMARY, fg=TEXT_COLOR, insertbackground=TEXT_COLOR,
            font=FONT_MAIN, relief="flat", bd=0,
        )
        search_entry.pack(fill="x", ipady=4)
        tk.Frame(search_frame, bg=ACCENT, height=2).pack(fill="x")

        # Listbox
        list_frame = tk.Frame(left, bg=BG_SECONDARY)
        list_frame.pack(fill="both", expand=True, padx=10, pady=(0, 6))

        self._macro_listbox = tk.Listbox(
            list_frame,
            bg=BG_PRIMARY, fg=TEXT_COLOR, font=FONT_MAIN,
            selectbackground=ACCENT, selectforeground=TEXT_COLOR,
            activestyle="none", relief="flat", bd=0,
            highlightthickness=0,
        )
        self._macro_listbox.pack(fill="both", expand=True)
        self._macro_listbox.bind("<<ListboxSelect>>", self._on_macro_select)
        self._macro_listbox.bind("<Button-3>", self._on_lib_right_click)
        self._macro_listbox.bind("<Motion>", self._on_lib_hover)
        self._macro_listbox.bind("<Leave>", self._on_lib_hover_leave)
        self._lib_hover_idx = -1

        # Library context menu
        self._lib_ctx = tk.Menu(self, tearoff=0, bg=BG_SECONDARY,
                                fg=TEXT_COLOR, activebackground=ACCENT,
                                activeforeground=TEXT_COLOR)
        self._lib_ctx.add_command(label="Rename",    command=self._on_rename_macro)
        self._lib_ctx.add_command(label="Duplicate", command=self._on_duplicate_macro)
        self._lib_ctx.add_separator()
        self._lib_ctx.add_command(label="Delete",    command=self._on_delete_macro)

        # "+ New Macro" button
        new_btn = tk.Button(
            left, text="＋ New Macro", font=FONT_BOLD,
            bg=ACCENT, fg=TEXT_COLOR, activebackground=ACCENT_HOVER,
            activeforeground=TEXT_COLOR, relief="flat", bd=0,
            cursor="hand2", command=self._on_new_macro,
        )
        new_btn.pack(fill="x", padx=10, pady=(0, 10), ipady=6)

        # -- Right panel: action list ------------------------------------
        right = tk.Frame(container, bg=BG_PRIMARY)
        right.pack(side="left", fill="both", expand=True)

        columns = ("#", "Icon", "Action", "Value", "Comment")
        self._action_tree = ttk.Treeview(
            right, columns=columns, show="headings",
            style="Dark.Treeview", selectmode="extended",
        )

        col_widths = {"#": 40, "Icon": 30, "Action": 160,
                      "Value": 320, "Comment": 150}
        for col in columns:
            self._action_tree.heading(col, text=col, anchor="w")
            self._action_tree.column(
                col, width=col_widths[col], minwidth=30, anchor="w",
            )

        vsb = ttk.Scrollbar(right, orient="vertical",
                            command=self._action_tree.yview,
                            style="Dark.Vertical.TScrollbar")
        self._action_tree.configure(yscrollcommand=vsb.set)

        self._action_tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        # Alternate row tags
        self._action_tree.tag_configure("row_a", background=ROW_ALT_A)
        self._action_tree.tag_configure("row_b", background=ROW_ALT_B)
        self._action_tree.tag_configure("selected", background=ACCENT)

        # Bindings
        self._action_tree.bind("<Double-1>", self._on_edit_action_dbl)
        self._action_tree.bind("<Button-3>", self._on_action_right_click)

        # Action context menu
        self._action_ctx = tk.Menu(self, tearoff=0, bg=BG_SECONDARY,
                                   fg=TEXT_COLOR, activebackground=ACCENT,
                                   activeforeground=TEXT_COLOR)
        self._action_ctx.add_command(label="Edit",      command=self._on_edit_action)
        self._action_ctx.add_command(label="Duplicate", command=self._on_dup_action)
        self._action_ctx.add_separator()
        self._action_ctx.add_command(label="Move Up",   command=self._on_move_up)
        self._action_ctx.add_command(label="Move Down",  command=self._on_move_down)
        self._action_ctx.add_separator()
        self._action_ctx.add_command(label="Delete",    command=self._on_delete_action)

        # -- Variables panel (collapsible, below action list) ---------------
        self._vars_panel = tk.Frame(container, bg=BG_SECONDARY)
        # Not packed initially — toggled via View menu

        vars_header_row = tk.Frame(self._vars_panel, bg=BG_SECONDARY)
        vars_header_row.pack(fill="x")
        tk.Label(vars_header_row, text="📋 Variables", font=FONT_BOLD,
                 bg=BG_SECONDARY, fg=TEXT_COLOR, anchor="w").pack(
            side="left", padx=10, pady=4)
        tk.Button(vars_header_row, text="Clear", font=FONT_SMALL,
                  bg=BG_PRIMARY, fg=TEXT_DIM, relief="flat", bd=0,
                  command=self._clear_variables).pack(side="right", padx=10)

        self._vars_text = tk.Text(
            self._vars_panel, height=4,
            bg=BG_PRIMARY, fg=TEXT_COLOR, insertbackground=TEXT_COLOR,
            font=("Consolas", 9), relief="flat", bd=0, wrap="word",
            state="disabled",
        )
        self._vars_text.pack(fill="x", padx=10, pady=(0, 6))

    # ===================================================================
    # Status bar
    # ===================================================================
    def _build_status_bar(self) -> tk.Frame:
        parent = self._content_area
        bar = tk.Frame(parent, bg=BG_SECONDARY, height=28)
        bar.pack(fill="x", side="bottom")
        bar.pack_propagate(False)

        # Left — status with dot
        left = tk.Frame(bar, bg=BG_SECONDARY)
        left.pack(side="left", padx=10)
        self._status_dot = tk.Canvas(left, width=10, height=10,
                                     bg=BG_SECONDARY, highlightthickness=0)
        self._status_dot.pack(side="left", pady=8)
        self._status_dot.create_oval(1, 1, 9, 9, fill=SUCCESS, outline="")
        self._status_label = tk.Label(left, text="Ready", font=FONT_SMALL,
                                      bg=BG_SECONDARY, fg=TEXT_COLOR)
        self._status_label.pack(side="left", padx=(4, 0))

        # Centre — event count
        self._count_label = tk.Label(bar, text="0 events", font=FONT_SMALL,
                                     bg=BG_SECONDARY, fg=TEXT_DIM)
        self._count_label.pack(side="left", expand=True)

        # Right — network | duration | speed
        right = tk.Frame(bar, bg=BG_SECONDARY)
        right.pack(side="right", padx=10)

        self._net_label = tk.Label(right, text="🌐 Direct", font=FONT_SMALL,
                                    bg=BG_SECONDARY, fg=TEXT_DIM,
                                    cursor="hand2")
        self._net_label.pack(side="left", padx=(0, 8))
        self._net_label.bind("<Button-1>", lambda e: self._on_network())
        tk.Label(right, text="|", font=FONT_SMALL,
                 bg=BG_SECONDARY, fg=BORDER_COLOR).pack(side="left")

        self._dur_label = tk.Label(right, text="0.0 s", font=FONT_SMALL,
                                   bg=BG_SECONDARY, fg=TEXT_DIM)
        self._dur_label.pack(side="left", padx=(8, 8))
        tk.Label(right, text="|", font=FONT_SMALL,
                 bg=BG_SECONDARY, fg=BORDER_COLOR).pack(side="left")
        self._speed_label = tk.Label(right, text="1.0×", font=FONT_SMALL,
                                     bg=BG_SECONDARY, fg=TEXT_DIM)
        self._speed_label.pack(side="left", padx=(8, 0))

        # ── Playback progress bar (hidden until playing) ─────
        self._progress_frame = tk.Frame(self._content_area, bg=BG_SECONDARY, height=20)
        # Not packed initially — shown during playback

        self._progress_label = tk.Label(
            self._progress_frame, text="", font=FONT_SMALL,
            bg=BG_SECONDARY, fg=TEXT_COLOR,
        )
        self._progress_label.pack(side="left", padx=10)

        self._progress_canvas = tk.Canvas(
            self._progress_frame, height=12, bg=BG_PRIMARY,
            highlightthickness=0,
        )
        self._progress_canvas.pack(side="left", fill="x", expand=True, padx=(0, 10), pady=4)

        return bar

    # ===================================================================
    # Public helpers — call from App / controller
    # ===================================================================
    def set_status(self, status: str):
        """Update the status bar text and dot colour."""
        self._status = status
        self._status_label.config(text=status)
        colours = {
            "Ready": "#2ecc71",
            "Saved": "#2ecc71",
            "Recording...": "#e74c3c",
            "Playing...": "#f39c12",
            "Paused": TEXT_DIM,
        }
        dot_col = colours.get(status, TEXT_DIM)
        self._status_dot.delete("all")
        self._status_dot.create_oval(1, 1, 9, 9, fill=dot_col, outline="")

        # Update tray icon state to match
        tray = self._tray or (self._app.tray if self._app and hasattr(self._app, 'tray') else None)
        if tray:
            tray_map = {
                "Recording...": "recording",
                "Playing...": "playing",
            }
            tray.set_state(tray_map.get(status, "idle"))

    def set_event_count(self, n: int):
        self._event_count = n
        self._count_label.config(text=f"{n} event{'s' if n != 1 else ''}")

    def set_duration(self, seconds: float):
        self._duration = seconds
        self._dur_label.config(text=f"{seconds:.1f} s")

    def set_speed(self, multiplier: float):
        self._speed = multiplier
        self._speed_label.config(text=f"{multiplier:.1f}×")

    def show_playback_progress(self, current: int, total: int,
                                loop: int, total_loops: int):
        """Update the playback progress bar (called from player thread via after())."""
        if not self._progress_frame.winfo_ismapped():
            self._progress_frame.pack(fill="x", side="bottom",
                                       before=self._status_bar)

        loop_str = f"Loop {loop}" + (f"/{total_loops}" if total_loops else " (∞)")
        self._progress_label.config(
            text=f"Playing: {current}/{total} events  {loop_str}"
        )

        # Draw progress bar
        w = self._progress_canvas.winfo_width()
        if w < 10:
            w = 400
        pct = current / total if total else 0
        self._progress_canvas.delete("all")
        self._progress_canvas.create_rectangle(
            0, 0, int(w * pct), 12, fill=WARNING, outline=""
        )

    def hide_playback_progress(self):
        """Hide progress bar when playback finishes."""
        self._progress_frame.pack_forget()
        self._progress_label.config(text="")
        self._progress_canvas.delete("all")

    def load_actions(self, events: list[dict]):
        """Populate the action Treeview from a list of event dicts."""
        self._loaded_events = list(events)  # cache full event data
        self._action_tree.delete(*self._action_tree.get_children())
        icon_map = {
            "click": "🖱", "move": "↗", "scroll": "🔄",
            "key_press": "⌨", "key_release": "⌨",
            "wait": "⏱", "delay": "⏱", "wait_seconds": "⏱",
            "run_app": "🚀", "window_focus": "🪟", "key_combo": "⌨",
            "save_variable": "📋", "find_image": "🔍",
        }
        for i, ev in enumerate(events):
            action = ev.get("type", ev.get("action", "unknown"))
            icon = icon_map.get(action, "•")
            value = self._event_value_str(ev)
            comment = ev.get("comment", "")
            tag = "row_a" if i % 2 == 0 else "row_b"
            self._action_tree.insert(
                "", "end",
                values=(i + 1, icon, action, value, comment),
                tags=(tag,),
            )
        self.set_event_count(len(events))

    # ===================================================================
    # Internal — macro library helpers
    # ===================================================================
    def _macro_dir(self) -> Path:
        d = Path(config.MACROS_DIR)
        d.mkdir(parents=True, exist_ok=True)
        return d

    def _refresh_macro_library(self, filter_text: str = ""):
        self._macro_listbox.delete(0, "end")
        self._macros.clear()
        macro_dir = self._macro_dir()
        for f in sorted(macro_dir.glob("*.json")):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
            except Exception:
                continue
            meta = data.get("metadata", {})
            name = meta.get("name", data.get("name", f.stem))
            events = data.get("events", [])
            dur = meta.get("duration_seconds", data.get("duration", 0))
            if filter_text and filter_text.lower() not in name.lower():
                continue
            self._macros.append({"path": f, "name": name,
                                 "events": events, "duration": dur})
            display = f"{name}  ({len(events)} events · {dur:.1f}s)"
            self._macro_listbox.insert("end", display)

    def _selected_macro(self) -> dict | None:
        sel = self._macro_listbox.curselection()
        if not sel:
            return None
        return self._macros[sel[0]]

    @staticmethod
    def _event_value_str(ev: dict) -> str:
        t = ev.get("type", ev.get("action", ""))
        if t in ("click", "move"):
            x, y = ev.get("x", "?"), ev.get("y", "?")
            btn = ev.get("button", "")
            return f"({x}, {y})" + (f"  {btn}" if btn else "")
        if t in ("key_press", "key_release"):
            return ev.get("key", "")
        if t in ("wait", "delay"):
            return f"{ev.get('seconds', ev.get('delay', 0)):.3f}s"
        if t == "wait_seconds":
            return f"{ev.get('value', '0')}s"
        if t == "scroll":
            return f"dx={ev.get('dx', 0)} dy={ev.get('dy', 0)}"
        if t in ("run_app", "window_focus", "key_combo", "save_variable", "find_image"):
            return ev.get("value", "")
        return str({k: v for k, v in ev.items() if k not in ("type", "timestamp")})

    # ===================================================================
    # Callbacks — toolbar / menu
    # ===================================================================
    def _on_play(self):
        if self._recorder.is_recording:
            messagebox.showwarning("Busy", "Stop recording before playing.",
                                   parent=self)
            return
        if self._player.is_playing:
            return

        # Determine which macro to play
        m = self._selected_macro()
        macro_name = m["name"] if m else self._current_macro_name

        # Load from store (returns typed event objects)
        events = self._store.load(macro_name)
        if not events:
            messagebox.showinfo("Play",
                                f"No events in '{macro_name}'.\n"
                                "Record or open a macro first.",
                                parent=self)
            return

        loops = self.get_loop_count()
        self._player.speed_multiplier = self._speed

        # Progress callback (player thread → GUI via after())
        def _progress(cur, total, loop, total_loops):
            self.after(0, self.show_playback_progress,
                       cur, total, loop, total_loops)
        self._player._on_progress = _progress

        def _done():
            self.after(0, self._playback_finished)

        self.set_status("Playing...")

        # Build on_each_loop_done for proxy rotation
        def _on_each_loop(loop_num):
            pm = getattr(self._app, "proxy_manager", None) if self._app else None
            if pm is None:
                pm = getattr(self, "_proxy_manager", None)
            if pm and pm.mode != "direct" and pm.rotation_mode == "after_macro":
                pm.rotate()
                new = pm.current_proxy
                # Update env vars immediately
                current = pm.get_current()
                if current:
                    import os
                    os.environ['HTTP_PROXY']  = current.get('http', '')
                    os.environ['HTTPS_PROXY'] = current.get('https', '')
                    os.environ['http_proxy']  = current.get('http', '')
                    os.environ['https_proxy'] = current.get('https', '')
                new_ip = f"{new.host}:{new.port}" if new else "Unknown"
                self.after(0, lambda ip=new_ip:
                    self.update_network_status(f"🔄 Rotated → {ip}"))
                print(f"[GUI] ✅ Loop {loop_num} done — IP rotated to {new_ip}")

        self._player.replay(events, loops=loops,
                            on_each_loop_done=_on_each_loop,
                            on_done=_done)

    def _playback_finished(self):
        self.set_status("Ready")
        self.hide_playback_progress()

    def _on_record(self):
        if self._player.is_playing:
            messagebox.showwarning("Busy", "Stop playback before recording.",
                                   parent=self)
            return
        if self._recorder.is_recording:
            return

        self.set_status("Recording...")
        self._recorder.start()

        # Show recording overlay
        if self._rec_overlay:
            self._rec_overlay.stop()
        self._rec_overlay = RecordingOverlay(self, on_stop=self._on_stop)
        self._start_rec_overlay_updates()

    def _on_stop(self):
        """Stop whatever is currently running (recording or playback)."""
        if self._recorder.is_recording:
            self._stop_recording()
        if self._player.is_playing:
            self._stop_playback()

    def _stop_recording(self):
        """Stop recording, save macro, refresh library."""
        self._cancel_rec_overlay_updates()
        events = self._recorder.stop()

        if self._rec_overlay:
            self._rec_overlay.stop()
            self._rec_overlay = None

        self.set_status("Ready")

        if not events:
            return

        # Save through MacroStore
        self._store.save(self._current_macro_name, events)
        self._refresh_macro_library()

        # Show recorded events in action list
        event_dicts = [e.to_dict() for e in events]
        self.load_actions(event_dicts)
        self.set_duration(self._recorder.get_duration())

    def _stop_playback(self):
        """Abort playback."""
        self._player.abort()
        self.set_status("Ready")
        self.hide_playback_progress()

    def _start_rec_overlay_updates(self):
        """Periodically push event count to the recording overlay."""
        if self._recorder.is_recording and self._rec_overlay:
            self._rec_overlay.set_event_count(len(self._recorder.events))
            self._rec_update_id = self.after(
                500, self._start_rec_overlay_updates)

    def _cancel_rec_overlay_updates(self):
        if self._rec_update_id is not None:
            self.after_cancel(self._rec_update_id)
            self._rec_update_id = None

    def _on_pause(self):
        # Player doesn't support true pause; stop playback instead
        if self._player.is_playing:
            self._stop_playback()
            self.set_status("Paused")

    def _on_set_speed(self):
        def apply_speed(val):
            self.set_speed(val)
            self._player.speed_multiplier = val
        open_speed_dialog(self, current_speed=self._speed, on_apply=apply_speed)

    # -- Insert actions ---------------------------------------------------
    def _on_insert_mouse(self):
        result = open_action_editor(self, action={"type": "left_click"})
        if result:
            self._append_action(result)

    def _on_insert_key(self):
        result = open_action_editor(self, action={"type": "key_press"})
        if result:
            self._append_action(result)

    def _on_insert_wait(self):
        result = open_action_editor(self, action={"type": "wait"})
        if result:
            self._append_action(result)

    def _on_insert_image(self):
        result = open_action_editor(self, action={"type": "find_image"})
        if result:
            self._append_action(result)

    def _append_action(self, ev: dict):
        children = self._action_tree.get_children()
        idx = len(children) + 1
        icon_map = {"click": "🖱", "key_press": "⌨", "wait": "⏱"}
        tag = "row_a" if idx % 2 == 1 else "row_b"
        self._action_tree.insert(
            "", "end",
            values=(idx, icon_map.get(ev.get("type", ""), "•"),
                    ev.get("type", ""), self._event_value_str(ev), ""),
            tags=(tag,),
        )
        # Keep _loaded_events in sync
        self._loaded_events.append(ev)
        self.set_event_count(idx)

    # -- Edit / delete actions -------------------------------------------
    def _on_edit_action(self):
        sel = self._action_tree.selection()
        if not sel:
            messagebox.showinfo("Edit", "Select an action to edit first.",
                                parent=self)
            return
        item = sel[0]
        vals = self._action_tree.item(item, "values")
        existing = {"type": vals[2], "value": vals[3], "comment": vals[4]}
        result = open_action_editor(self, action=existing)
        if result:
            icon_map = {
                "click": "🖱", "move": "↗", "scroll": "🔄",
                "key_press": "⌨", "key_release": "⌨",
                "wait": "⏱", "delay": "⏱",
                "mouse_move": "↗", "left_click": "🖱", "right_click": "🖱",
                "double_click": "🖱", "scroll_up": "🔄", "scroll_down": "🔄",
                "type_text": "⌨", "key_combo": "⌨",
                "wait_screen_change": "⏱", "repeat_loop": "🔁",
                "find_image": "🔍", "find_text": "🔍",
                "run_app": "💾", "save_variable": "💾", "window_focus": "💾",
            }
            icon = icon_map.get(result.get("type", ""), "•")
            value = self._event_value_str(result)
            comment = result.get("comment", "")
            self._action_tree.item(item, values=(vals[0], icon, result["type"], value, comment))
            # Keep _loaded_events in sync
            edit_idx = self._action_tree.index(item)
            if edit_idx < len(self._loaded_events):
                self._loaded_events[edit_idx] = result

    def _on_edit_action_dbl(self, _e):
        self._on_edit_action()

    def _on_dup_action(self):
        sel = self._action_tree.selection()
        if not sel:
            return
        for item in sel:
            vals = self._action_tree.item(item, "values")
            idx = len(self._action_tree.get_children()) + 1
            tag = "row_a" if idx % 2 == 1 else "row_b"
            self._action_tree.insert("", "end", values=(idx, *vals[1:]),
                                     tags=(tag,))
            # Keep _loaded_events in sync
            src_idx = self._action_tree.index(item)
            if src_idx < len(self._loaded_events):
                import copy
                self._loaded_events.append(copy.deepcopy(self._loaded_events[src_idx]))
        self.set_event_count(len(self._action_tree.get_children()))

    def _on_delete_action(self):
        sel = self._action_tree.selection()
        if not sel:
            messagebox.showinfo("Delete", "Select one or more actions to delete.",
                                parent=self)
            return
        self._push_undo_state()
        # Collect indices before deleting (reverse order to preserve indices)
        indices = sorted([self._action_tree.index(item) for item in sel], reverse=True)
        for item in sel:
            self._action_tree.delete(item)
        # Keep _loaded_events in sync
        for idx in indices:
            if 0 <= idx < len(self._loaded_events):
                self._loaded_events.pop(idx)
        self._renumber_actions()

    def _on_move_up(self):
        sel = self._action_tree.selection()
        if sel:
            self._push_undo_state()
        for item in sel:
            idx = self._action_tree.index(item)
            if idx > 0:
                self._action_tree.move(item, "", idx - 1)
                # Keep _loaded_events in sync
                if idx < len(self._loaded_events):
                    self._loaded_events[idx - 1], self._loaded_events[idx] = \
                        self._loaded_events[idx], self._loaded_events[idx - 1]
        self._renumber_actions()

    def _on_move_down(self):
        sel = self._action_tree.selection()
        if sel:
            self._push_undo_state()
        for item in reversed(sel):
            idx = self._action_tree.index(item)
            if idx < len(self._action_tree.get_children()) - 1:
                self._action_tree.move(item, "", idx + 1)
                # Keep _loaded_events in sync
                if idx + 1 < len(self._loaded_events):
                    self._loaded_events[idx], self._loaded_events[idx + 1] = \
                        self._loaded_events[idx + 1], self._loaded_events[idx]
        self._renumber_actions()

    def _on_search_actions(self):
        open_search_replace(self, self._action_tree)

    def _on_network(self):
        """Open the Network & Proxy Settings dialog."""
        pm = getattr(self._app, "proxy_manager", None) if self._app else None
        if pm is None:
            from features.proxy_manager import ProxyManager
            if not hasattr(self, "_proxy_manager"):
                self._proxy_manager = ProxyManager()
            pm = self._proxy_manager
        open_network_dialog(self, pm)
        # Update the status bar label after dialog closes
        self._update_net_label()

    def _update_net_label(self):
        """Refresh the network indicator in the status bar."""
        pm = getattr(self._app, "proxy_manager", None) if self._app else None
        if pm is None:
            pm = getattr(self, "_proxy_manager", None)
        if pm is None:
            return
        mode = pm.mode
        if mode == "direct":
            self._net_label.config(text="🌐 Direct", fg=TEXT_DIM)
        elif mode == "tor":
            self._net_label.config(text="🧅 Tor", fg=TEXT_DIM)
        elif mode == "proxy":
            cur = pm.current_proxy
            if cur:
                self._net_label.config(text=f"🌐 Proxy: {cur.host}", fg=TEXT_DIM)
            else:
                self._net_label.config(text="🌐 Proxy (none)", fg=TEXT_DIM)

    def update_network_status(self, text: str):
        """Flash the network label orange, show text, then restore after 3s."""
        self._net_label.config(text=text, fg=WARNING)
        self.after(3000, self._restore_network_status)

    def _restore_network_status(self):
        """Return network label to normal colour and current proxy info."""
        self._update_net_label()

    def _start_net_status_timer(self):
        """Auto-refresh network status every 30 seconds."""
        self._update_net_label()
        self.after(30000, self._start_net_status_timer)

    def _renumber_actions(self):
        for i, item in enumerate(self._action_tree.get_children()):
            vals = list(self._action_tree.item(item, "values"))
            vals[0] = i + 1
            tag = "row_a" if i % 2 == 0 else "row_b"
            self._action_tree.item(item, values=vals, tags=(tag,))
        self.set_event_count(len(self._action_tree.get_children()))

    # -- Library callbacks -----------------------------------------------
    # -- Tray app proxy ---------------------------------------------------
    def _make_tray_app_proxy(self):
        """Return a lightweight object that satisfies TrayIcon's app API."""
        class _Proxy:
            pass
        proxy = _Proxy()
        proxy.start_recording = lambda: self.after(0, self._on_record)
        proxy.stop_recording = lambda: self.after(0, self._on_stop)
        proxy.replay = lambda: self.after(0, self._on_play)
        proxy.abort = lambda: self.after(0, self._on_stop)
        proxy.quit = lambda: self.after(0, self._on_exit)
        proxy.window = self
        proxy.store = self._store
        return proxy

    # -- Listbox hover highlight ----------------------------------------
    def _on_lib_hover(self, event):
        idx = self._macro_listbox.nearest(event.y)
        if idx == self._lib_hover_idx:
            return
        # Remove old highlight
        if 0 <= self._lib_hover_idx < self._macro_listbox.size():
            self._macro_listbox.itemconfigure(self._lib_hover_idx, bg=BG_PRIMARY)
        # Apply new highlight
        if 0 <= idx < self._macro_listbox.size():
            self._macro_listbox.itemconfigure(idx, bg=BORDER_COLOR)
        self._lib_hover_idx = idx

    def _on_lib_hover_leave(self, _event):
        if 0 <= self._lib_hover_idx < self._macro_listbox.size():
            self._macro_listbox.itemconfigure(self._lib_hover_idx, bg=BG_PRIMARY)
        self._lib_hover_idx = -1

    def _on_macro_select(self, _e):
        m = self._selected_macro()
        if m:
            self._current_macro_name = m["name"]
            self.load_actions(m["events"])
            self.set_duration(m["duration"])

    def _on_lib_right_click(self, e):
        self._macro_listbox.select_clear(0, "end")
        idx = self._macro_listbox.nearest(e.y)
        self._macro_listbox.selection_set(idx)
        self._lib_ctx.tk_popup(e.x_root, e.y_root)

    def _on_lib_search(self, *_):
        self._refresh_macro_library(self._lib_search_var.get())

    def _on_rename_macro(self):
        m = self._selected_macro()
        if not m:
            return
        new_name = simpledialog.askstring("Rename", "New name:",
                                          initialvalue=m["name"],
                                          parent=self)
        if not new_name or new_name == m["name"]:
            return
        # Use MacroStore.rename() which handles file + metadata update
        if self._store.rename(m["name"], new_name):
            if self._current_macro_name == m["name"]:
                self._current_macro_name = self._store._sanitize_name(new_name)
            self._refresh_macro_library()
        else:
            messagebox.showerror("Rename Error",
                                 f"Could not rename '{m['name']}' to '{new_name}'.",
                                 parent=self)

    def _on_duplicate_macro(self):
        m = self._selected_macro()
        if not m:
            return
        try:
            data = json.loads(m["path"].read_text(encoding="utf-8"))
            copy_name = m["name"] + "_copy"
            # Update metadata with new name
            if "metadata" in data:
                data["metadata"]["name"] = copy_name
                from datetime import datetime
                data["metadata"]["saved_at"] = datetime.now().isoformat()
            new_path = m["path"].with_stem(m["path"].stem + "_copy")
            # Avoid overwriting existing copies
            counter = 1
            while new_path.exists():
                counter += 1
                new_path = m["path"].with_stem(m["path"].stem + f"_copy{counter}")
                if "metadata" in data:
                    data["metadata"]["name"] = m["name"] + f"_copy{counter}"
            new_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
            self._refresh_macro_library()
        except Exception as exc:
            messagebox.showerror("Duplicate Error", str(exc), parent=self)

    def _on_delete_macro(self):
        m = self._selected_macro()
        if not m:
            messagebox.showinfo("Delete", "Select a macro first.", parent=self)
            return
        if messagebox.askyesno("Delete Macro",
                               f"Delete '{m['name']}'?\nThis cannot be undone.",
                               parent=self):
            try:
                if self._store.exists(m["name"]):
                    self._store.delete(m["name"])
                elif m["path"].exists():
                    m["path"].unlink()
                if self._current_macro_name == m["name"]:
                    self._current_macro_name = "macro1"
                self._refresh_macro_library()
                self._action_tree.delete(*self._action_tree.get_children())
                self.set_event_count(0)
                self.set_duration(0)
                self.set_status("Ready")
            except Exception as exc:
                messagebox.showerror("Delete Error", str(exc), parent=self)

    # -- File menu -------------------------------------------------------
    def _on_new_macro(self):
        name = simpledialog.askstring("New Macro", "Macro name:",
                                      parent=self)
        if not name:
            return
        safe_name = self._store._sanitize_name(name)
        path = self._macro_dir() / f"{safe_name}.json"
        if path.exists():
            messagebox.showwarning("Exists",
                                   f"Macro '{safe_name}' already exists.",
                                   parent=self)
            return
        from datetime import datetime
        data = {
            "metadata": {
                "name": safe_name,
                "event_count": 0,
                "duration_seconds": 0,
                "saved_at": datetime.now().isoformat(),
            },
            "events": [],
        }
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        self._current_macro_name = safe_name
        self._refresh_macro_library()
        self._action_tree.delete(*self._action_tree.get_children())
        self.set_event_count(0)
        self.set_duration(0)

    def _on_open(self):
        path = filedialog.askopenfilename(
            filetypes=[("JSON macros", "*.json"), ("All files", "*.*")],
            initialdir=str(self._macro_dir()), parent=self,
        )
        if not path:
            return
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
            self.load_actions(data.get("events", []))
            self._current_macro_name = Path(path).stem
            self.set_duration(
                data.get("metadata", {}).get("duration_seconds",
                data.get("duration", 0))
            )
        except Exception as exc:
            messagebox.showerror("Open Error", str(exc), parent=self)

    def _on_save(self):
        m = self._selected_macro()
        if not m:
            self._on_save_as()
            return
        self._write_current_to(m["path"], m["name"])

    def _on_save_as(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON macros", "*.json")],
            initialdir=str(self._macro_dir()), parent=self,
        )
        if not path:
            return
        self._write_current_to(Path(path), Path(path).stem)
        self._refresh_macro_library()

    def _write_current_to(self, path: Path, name: str):
        """Save the current macro back to disk, preserving full event data."""
        tree_count = len(self._action_tree.get_children())

        # Use cached full event data if available and matching
        if self._loaded_events and len(self._loaded_events) == tree_count:
            events = self._loaded_events
        else:
            # Try to reload original event data from disk
            original_events = None
            if path.exists():
                try:
                    orig_data = json.loads(path.read_text(encoding="utf-8"))
                    original_events = orig_data.get("events", [])
                except Exception:
                    pass

            if original_events and len(original_events) == tree_count:
                events = original_events
            else:
                # Fallback: reconstruct from treeview (limited data)
                events = []
                for item in self._action_tree.get_children():
                    vals = self._action_tree.item(item, "values")
                    events.append({
                        "type": vals[2],
                        "value": vals[3],
                        "comment": vals[4] if len(vals) > 4 else "",
                    })

        from datetime import datetime
        data = {
            "metadata": {
                "name": name,
                "event_count": len(events),
                "duration_seconds": self._duration,
                "saved_at": datetime.now().isoformat(),
            },
            "events": events,
        }
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        self.set_status("Saved")
        self._refresh_macro_library()

    def _on_exit(self):
        if self._recorder.is_recording:
            self._stop_recording()
        if self._player.is_playing:
            self._player.abort()
        self._cancel_rec_overlay_updates()
        if self._app:
            # Running under App — let App handle full shutdown
            self._app.quit()
        else:
            # Standalone mode
            if self._tray:
                self._tray.stop()
            self.destroy()

    # -- Edit menu / Undo Redo -------------------------------------------
    def _push_undo_state(self):
        import copy
        self._undo_stack.append(copy.deepcopy(self._loaded_events))
        self._redo_stack.clear()
        
    def _on_undo(self):
        if not self._undo_stack:
            return
        import copy
        self._redo_stack.append(copy.deepcopy(self._loaded_events))
        self._loaded_events = self._undo_stack.pop()
        self._refresh_action_list()
        self._save_current_silently()

    def _on_redo(self):
        if not self._redo_stack:
            return
        import copy
        self._undo_stack.append(copy.deepcopy(self._loaded_events))
        self._loaded_events = self._redo_stack.pop()
        self._refresh_action_list()
        self._save_current_silently()
        
    def _on_import(self):
        filepath = filedialog.askopenfilename(title="Import Macro", filetypes=[("JSON Files", "*.json")])
        if filepath:
            try:
                import json
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if isinstance(data, list):
                    self._push_undo_state()
                    self._loaded_events.extend(data)
                    self._refresh_action_list()
                    self._save_current_silently()
                    self._log_console.log(f"Imported {len(data)} actions from {os.path.basename(filepath)}")
                else:
                    raise ValueError("Invalid format: expected JSON array of events")
            except Exception as e:
                messagebox.showerror("Import Error", str(e))
                
    def _on_export(self):
        filepath = filedialog.asksaveasfilename(title="Export Macro", defaultextension=".json", filetypes=[("JSON Files", "*.json")])
        if filepath:
            try:
                import json
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(self._loaded_events, f, indent=2)
                self._log_console.log(f"Exported {len(self._loaded_events)} actions to {os.path.basename(filepath)}")
            except Exception as e:
                messagebox.showerror("Export Error", str(e))

    def _on_select_all(self):
        for item in self._action_tree.get_children():
            self._action_tree.selection_add(item)

    # -- Action right‑click ----------------------------------------------
    def _on_action_right_click(self, e):
        row = self._action_tree.identify_row(e.y)
        if row:
            self._action_tree.selection_set(row)
            self._action_ctx.tk_popup(e.x_root, e.y_root)

    # -- View menu -------------------------------------------------------
    def _toggle_toolbar(self):
        if self._show_toolbar.get():
            self._toolbar_frame.pack(fill="x", side="top",
                                     before=self._main_container)
        else:
            self._toolbar_frame.pack_forget()

    def _toggle_statusbar(self):
        if self._show_statusbar.get():
            self._status_bar.pack(fill="x", side="bottom")
        else:
            self._status_bar.pack_forget()

    def _toggle_variables(self):
        if self._vars_visible.get():
            self._vars_panel.pack(side="bottom", fill="x", padx=4, pady=(0, 4))
        else:
            self._vars_panel.pack_forget()

    def update_variables_display(self, var_dict: dict[str, str]):
        """Refresh the variables panel with current key=value pairs."""
        self._vars_text.config(state="normal")
        self._vars_text.delete("1.0", "end")
        if var_dict:
            for k, v in sorted(var_dict.items()):
                self._vars_text.insert("end", f"{k} = {v}\n")
        else:
            self._vars_text.insert("end", "(no variables)")
        self._vars_text.config(state="disabled")

    def _clear_variables(self):
        self._player.variables.clear()
        self.update_variables_display({})

    # -- Help menu -------------------------------------------------------
    def _on_about(self):
        messagebox.showinfo(
            "About",
            "⚡ Macro Recorder Pro\n\n"
            "Version 2.0\n"
            "AI-Powered Desktop Automation.\n\n"
            "Built with Python + CustomTkinter.\n"
            "Supports Gemini, OpenAI & Claude AI.",
            parent=self,
        )

    def _on_docs(self):
        messagebox.showinfo(
            "Documentation",
            "See README.md and the numbered guide files\n"
            "in the project root for full documentation.",
            parent=self,
        )


# -----------------------------------------------------------------------
# Standalone launch (for testing without main.py)
# -----------------------------------------------------------------------
if __name__ == "__main__":
    app_win = MacroRecorderWindow(app=None)

    # Demo: insert some sample actions
    sample_events = [
        {"type": "click", "x": 150, "y": 300, "button": "left"},
        {"type": "wait", "seconds": 0.5},
        {"type": "key_press", "key": "a"},
        {"type": "move", "x": 400, "y": 200},
        {"type": "scroll", "dx": 0, "dy": -3},
        {"type": "click", "x": 600, "y": 100, "button": "right"},
        {"type": "wait", "seconds": 1.0},
        {"type": "key_press", "key": "Enter"},
    ]
    app_win.load_actions(sample_events)
    app_win.set_duration(3.75)
    app_win.set_speed(1.0)

    app_win.mainloop()
