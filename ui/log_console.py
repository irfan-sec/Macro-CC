import sys
import datetime
import tkinter as tk
import customtkinter as ctk

from ui.theme import BG_PRIMARY, BG_SECONDARY, ACCENT, ACCENT_HOVER, TEXT_COLOR, TEXT_DIM, BORDER_COLOR, SUCCESS, WARNING

class StdoutRedirector:
    """Captures stdout and redirects it to the log console, while keeping original stdout."""
    def __init__(self, console, original_stdout):
        self.console = console
        self.original_stdout = original_stdout

    def write(self, message):
        # Still write to the original stdout
        self.original_stdout.write(message)
        
        # Avoid logging empty lines from print() trailing newlines
        msg = message.strip()
        if not msg:
            return

        # Determine log level based on prefix
        level = 'info'
        if msg.startswith('[Player]'):
            level = 'success'
        elif msg.startswith('[Recorder]'):
            level = 'warning'
        elif msg.startswith('[App]'):
            level = 'info'
        elif msg.startswith('[AI]'):
            level = 'ai'
        elif '[Error]' in msg or msg.startswith('Error:'):
            level = 'error'

        # Use after to safely update the GUI from other threads
        self.console.after(0, self.console.log, msg, level)

    def flush(self):
        self.original_stdout.flush()


class LogConsole(ctk.CTkFrame):
    """A real-time log console panel."""
    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color=BG_PRIMARY, **kwargs)
        
        self.is_collapsed = False
        self.max_lines = 500
        self.original_stdout = sys.stdout

        # Header Bar
        self.header_frame = ctk.CTkFrame(self, fg_color=BG_SECONDARY, corner_radius=0, height=30)
        self.header_frame.pack(fill="x", side="top")
        self.header_frame.pack_propagate(False)

        self.title_label = ctk.CTkLabel(
            self.header_frame, 
            text="📋 Console", 
            text_color=TEXT_COLOR, 
            font=("Segoe UI", 12, "bold")
        )
        self.title_label.pack(side="left", padx=10)

        self.toggle_btn = ctk.CTkButton(
            self.header_frame, 
            text="▼", 
            width=30, 
            height=20, 
            fg_color="transparent", 
            hover_color=BG_PRIMARY, 
            text_color=TEXT_COLOR, 
            command=self.toggle
        )
        self.toggle_btn.pack(side="right", padx=5, pady=5)

        self.clear_btn = ctk.CTkButton(
            self.header_frame, 
            text="Clear", 
            width=50, 
            height=20, 
            fg_color=BORDER_COLOR, 
            hover_color=ACCENT_HOVER, 
            text_color=TEXT_COLOR, 
            font=("Segoe UI", 10), 
            command=self.clear
        )
        self.clear_btn.pack(side="right", padx=5, pady=5)

        # Body (Text widget)
        self.text_widget = tk.Text(
            self, 
            bg=BG_PRIMARY, 
            fg=TEXT_COLOR, 
            font=("Consolas", 9),
            wrap="word", 
            bd=0, 
            highlightthickness=0, 
            state="disabled"
        )
        self.text_widget.pack(fill="both", expand=True, padx=5, pady=5)

        # Configure color tags
        self.text_widget.tag_configure("info", foreground=TEXT_COLOR)
        self.text_widget.tag_configure("success", foreground=SUCCESS)
        self.text_widget.tag_configure("warning", foreground=WARNING)
        self.text_widget.tag_configure("error", foreground="#e74c3c")
        self.text_widget.tag_configure("ai", foreground="#3498db")
        self.text_widget.tag_configure("timestamp", foreground=TEXT_DIM)

    def log(self, message, level='info'):
        """Appends a timestamped log message with the specified level/color."""
        self.text_widget.config(state="normal")
        
        # Enforce max lines
        lines = int(self.text_widget.index('end-1c').split('.')[0])
        if lines > self.max_lines:
            self.text_widget.delete("1.0", f"{lines - self.max_lines + 1}.0")

        # Insert timestamp
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        self.text_widget.insert("end", f"[{timestamp}] ", "timestamp")
        
        # Insert message
        self.text_widget.insert("end", f"{message}\n", level)
        
        # Auto-scroll to bottom
        self.text_widget.see("end")
        self.text_widget.config(state="disabled")

    def clear(self):
        """Clears all text from the console."""
        self.text_widget.config(state="normal")
        self.text_widget.delete("1.0", "end")
        self.text_widget.config(state="disabled")

    def toggle(self):
        """Toggles the visibility of the text area (collapses/expands)."""
        self.is_collapsed = not self.is_collapsed
        if self.is_collapsed:
            self.text_widget.pack_forget()
            self.toggle_btn.configure(text="▲")
        else:
            self.text_widget.pack(fill="both", expand=True, padx=5, pady=5)
            self.toggle_btn.configure(text="▼")

    def capture_stdout(self):
        """Redirects stdout to this log console."""
        sys.stdout = StdoutRedirector(self, self.original_stdout)

    def restore_stdout(self):
        """Restores original stdout."""
        sys.stdout = self.original_stdout
