import tkinter as tk
import customtkinter as ctk
import config
from ui.theme import BG_PRIMARY, BG_SECONDARY, ACCENT, TEXT_COLOR, TEXT_DIM

class OnboardingWizard(ctk.CTkToplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Welcome to Macro Recorder Pro")
        self.geometry("600x450")
        self.resizable(False, False)
        self.configure(fg_color=BG_PRIMARY)
        
        # Center the window
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - (600 // 2)
        y = (self.winfo_screenheight() // 2) - (450 // 2)
        self.geometry(f"+{x}+{y}")
        
        self.attributes('-topmost', True)
        self.grab_set()

        self._build_ui()

    def _build_ui(self):
        title = ctk.CTkLabel(self, text="Welcome to Macro Recorder Pro! 🎉", font=("Segoe UI", 24, "bold"), text_color=TEXT_COLOR)
        title.pack(pady=(30, 10))
        
        subtitle = ctk.CTkLabel(self, text="Let's get your AI Assistant set up.", font=("Segoe UI", 14), text_color=TEXT_DIM)
        subtitle.pack(pady=(0, 30))

        # Setup frame
        frame = ctk.CTkFrame(self, fg_color=BG_SECONDARY, corner_radius=10)
        frame.pack(fill="both", expand=True, padx=40, pady=(0, 20))

        ctk.CTkLabel(frame, text="1. Select AI Provider", font=("Segoe UI", 14, "bold"), text_color=TEXT_COLOR).pack(anchor="w", padx=20, pady=(20, 5))
        
        self.provider_var = tk.StringVar(value=config.AI_PROVIDER)
        provider_menu = ctk.CTkOptionMenu(frame, values=["gemini", "openai", "claude"], variable=self.provider_var, command=self._on_provider_change)
        provider_menu.pack(anchor="w", padx=20, pady=(0, 15))

        ctk.CTkLabel(frame, text="2. Enter API Key", font=("Segoe UI", 14, "bold"), text_color=TEXT_COLOR).pack(anchor="w", padx=20, pady=(5, 5))
        
        self.key_entry = ctk.CTkEntry(frame, width=400, show="*", placeholder_text="Paste your API key here...")
        self.key_entry.pack(anchor="w", padx=20, pady=(0, 15))
        self._on_provider_change(self.provider_var.get())

        # Features list
        features = "✨ Build macros using natural language\n📸 Upload screenshots for UI automation\n⏰ Schedule macros to run in the background"
        ctk.CTkLabel(frame, text=features, justify="left", font=("Segoe UI", 13), text_color=TEXT_DIM).pack(anchor="w", padx=20, pady=(10, 20))

        # Bottom buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=40, pady=(0, 30))

        skip_btn = ctk.CTkButton(btn_frame, text="Skip", width=100, fg_color="transparent", hover_color=BG_SECONDARY, command=self._finish)
        skip_btn.pack(side="left")

        save_btn = ctk.CTkButton(btn_frame, text="Save & Get Started", width=150, fg_color=ACCENT, command=self._save_and_finish)
        save_btn.pack(side="right")

    def _on_provider_change(self, provider: str):
        self.key_entry.delete(0, tk.END)
        if provider == "gemini":
            self.key_entry.insert(0, config.GEMINI_API_KEY)
        elif provider == "openai":
            self.key_entry.insert(0, config.OPENAI_API_KEY)
        elif provider == "claude":
            self.key_entry.insert(0, config.CLAUDE_API_KEY)

    def _save_and_finish(self):
        provider = self.provider_var.get()
        api_key = self.key_entry.get().strip()
        
        config.AI_PROVIDER = provider
        if provider == "gemini":
            config.GEMINI_API_KEY = api_key
        elif provider == "openai":
            config.OPENAI_API_KEY = api_key
        elif provider == "claude":
            config.CLAUDE_API_KEY = api_key

        config.SHOW_ONBOARDING = False
        config.save_settings()
        self.destroy()

    def _finish(self):
        config.SHOW_ONBOARDING = False
        config.save_settings()
        self.destroy()

def show_onboarding_if_needed(master):
    if config.SHOW_ONBOARDING:
        OnboardingWizard(master)
