import customtkinter as ctk

try:
    from ui.theme import BG_PRIMARY, BG_SECONDARY, ACCENT, ACCENT_HOVER, TEXT_COLOR, TEXT_DIM, BORDER_COLOR
except ImportError:
    # Fallback theme colors
    BG_PRIMARY = "#1a1a2e"
    BG_SECONDARY = "#16213e"
    ACCENT = "#e94560"
    ACCENT_HOVER = "#ff6b81"
    TEXT_COLOR = "#ffffff"
    TEXT_DIM = "#8892b0"
    BORDER_COLOR = "#2a2a4a"

HOVER_BG = "#253255"

class SidebarItem(ctk.CTkFrame):
    """
    A single navigation item in the sidebar containing an icon and text.
    """
    def __init__(self, master, icon, text, command=None, **kwargs):
        super().__init__(master, fg_color="transparent", corner_radius=0, height=45, **kwargs)
        
        self.command = command
        self.text_val = text
        self.is_expanded = False
        self.is_active = False
        
        self.grid_columnconfigure(1, weight=0) # Icon column
        self.grid_columnconfigure(2, weight=1) # Text column
        self.grid_propagate(False)
        
        # Left accent bar (hidden by default)
        self.accent_bar = ctk.CTkFrame(self, width=4, height=45, fg_color="transparent", corner_radius=0)
        self.accent_bar.grid(row=0, column=0, sticky="ns")
        
        # Icon
        self.icon_label = ctk.CTkLabel(self, text=icon, width=56, height=45, font=("Segoe UI", 20), text_color=TEXT_DIM)
        self.icon_label.grid(row=0, column=1, sticky="w")
        
        # Text
        self.text_label = ctk.CTkLabel(self, text=text, height=45, font=("Segoe UI", 14), text_color=TEXT_DIM, anchor="w")
        
        # Bind events for hover and click
        for w in [self, self.accent_bar, self.icon_label, self.text_label]:
            w.bind("<Enter>", self.on_enter)
            w.bind("<Leave>", self.on_leave)
            w.bind("<Button-1>", self.on_click)

    def set_expanded(self, expanded):
        """Toggle text visibility based on sidebar state."""
        self.is_expanded = expanded
        if expanded:
            self.text_label.grid(row=0, column=2, sticky="ew", padx=(0, 10))
        else:
            self.text_label.grid_forget()
            
    def set_active(self, active):
        """Set the active state of the item."""
        self.is_active = active
        if active:
            self.accent_bar.configure(fg_color=ACCENT)
            self.icon_label.configure(text_color=TEXT_COLOR)
            self.text_label.configure(text_color=TEXT_COLOR)
            self.configure(fg_color=BG_SECONDARY)
        else:
            self.accent_bar.configure(fg_color="transparent")
            self.icon_label.configure(text_color=TEXT_DIM)
            self.text_label.configure(text_color=TEXT_DIM)
            self.configure(fg_color="transparent")

    def on_enter(self, event):
        """Hover effect."""
        if not self.is_active:
            self.configure(fg_color=HOVER_BG)
            self.icon_label.configure(text_color=TEXT_COLOR)
            self.text_label.configure(text_color=TEXT_COLOR)
            
    def on_leave(self, event):
        """Remove hover effect."""
        if not self.is_active:
            self.configure(fg_color="transparent")
            self.icon_label.configure(text_color=TEXT_DIM)
            self.text_label.configure(text_color=TEXT_DIM)
            
    def on_click(self, event):
        """Handle click event."""
        if self.command:
            self.command(self.text_val)


class Sidebar(ctk.CTkFrame):
    """
    Collapsible vertical sidebar for navigation.
    """
    def __init__(self, master, on_navigate, **kwargs):
        super().__init__(master, fg_color=BG_PRIMARY, corner_radius=0, width=60, **kwargs)
        
        self.on_navigate = on_navigate
        self.is_expanded = False
        
        # Prevent automatic resizing
        self.pack_propagate(False)
        self.grid_propagate(False)
        
        # Header (Hamburger Menu & App Title)
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent", height=60, corner_radius=0)
        self.header_frame.pack(fill="x", pady=(10, 10))
        self.header_frame.pack_propagate(False)
        
        self.toggle_btn = ctk.CTkButton(
            self.header_frame, 
            text="☰", 
            width=40, 
            height=40, 
            fg_color="transparent", 
            hover_color=HOVER_BG,
            text_color=TEXT_COLOR,
            font=("Segoe UI", 20),
            command=self.toggle_sidebar
        )
        self.toggle_btn.pack(side="left", padx=10)
        
        self.app_title = ctk.CTkLabel(
            self.header_frame, 
            text="Macro Pro", 
            font=("Segoe UI", 16, "bold"), 
            text_color=TEXT_COLOR,
            anchor="w"
        )
        
        # Navigation Items Container
        self.nav_items = {}
        
        nav_data = [
            ("🏠", "Home"),
            ("📁", "Macros"),
            ("✨", "AI Assistant"),
            ("⏰", "Scheduler"),
            ("🌐", "Network")
        ]
        
        self.nav_frame = ctk.CTkFrame(self, fg_color="transparent", corner_radius=0)
        self.nav_frame.pack(fill="both", expand=True)
        
        # Populate main navigation items
        for icon, text in nav_data:
            item = SidebarItem(self.nav_frame, icon, text, command=self._handle_navigate)
            item.pack(fill="x", pady=2)
            self.nav_items[text] = item
            
        # Bottom Items Container
        self.bottom_frame = ctk.CTkFrame(self, fg_color="transparent", corner_radius=0)
        self.bottom_frame.pack(fill="x", side="bottom", pady=10)
        
        # Settings Item
        self.settings_item = SidebarItem(self.bottom_frame, "⚙️", "Settings", command=self._handle_navigate)
        self.settings_item.pack(fill="x", pady=2)
        self.nav_items["Settings"] = self.settings_item
        
        # Set default active page
        self._set_active_item("Home")
        
    def toggle_sidebar(self):
        """Expand or collapse the sidebar."""
        self.is_expanded = not self.is_expanded
        
        target_width = 200 if self.is_expanded else 60
        self.configure(width=target_width)
        
        if self.is_expanded:
            self.app_title.pack(side="left", fill="x", expand=True, padx=(0, 10))
        else:
            self.app_title.pack_forget()
            
        for item in self.nav_items.values():
            item.set_expanded(self.is_expanded)
            
    def _handle_navigate(self, page_name):
        """Handle navigation item selection."""
        self._set_active_item(page_name)
        if self.on_navigate:
            self.on_navigate(page_name)
            
    def _set_active_item(self, page_name):
        """Update visual state of all items based on selection."""
        for name, item in self.nav_items.items():
            item.set_active(name == page_name)
