import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
import json
import os
import config

SETTINGS_FILE = os.path.join(config.BASE_DIR, "ai_settings.json")

def load_ai_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r") as f:
                data = json.load(f)
                config.AI_PROVIDER = data.get("AI_PROVIDER", config.AI_PROVIDER)
                config.GEMINI_API_KEY = data.get("GEMINI_API_KEY", config.GEMINI_API_KEY)
                config.OPENAI_API_KEY = data.get("OPENAI_API_KEY", config.OPENAI_API_KEY)
                config.CLAUDE_API_KEY = data.get("CLAUDE_API_KEY", config.CLAUDE_API_KEY)
        except Exception as e:
            print(f"Error loading AI settings: {e}")

def save_ai_settings(provider, gemini_key, openai_key, claude_key):
    data = {
        "AI_PROVIDER": provider,
        "GEMINI_API_KEY": gemini_key,
        "OPENAI_API_KEY": openai_key,
        "CLAUDE_API_KEY": claude_key
    }
    try:
        with open(SETTINGS_FILE, "w") as f:
            json.dump(data, f, indent=4)
        # Update config in memory
        config.AI_PROVIDER = provider
        config.GEMINI_API_KEY = gemini_key
        config.OPENAI_API_KEY = openai_key
        config.CLAUDE_API_KEY = claude_key
        return True
    except Exception as e:
        print(f"Error saving AI settings: {e}")
        return False


class AISettingsDialog(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("⚙️ AI Settings")
        self.geometry("450x350")
        self.transient(parent)
        self.grab_set()
        
        load_ai_settings() # Ensure memory is up-to-date

        # Title
        title = ctk.CTkLabel(self, text="AI Configuration", font=ctk.CTkFont(size=18, weight="bold"))
        title.pack(pady=(20, 10))

        # Provider Selection
        prov_frame = ctk.CTkFrame(self, fg_color="transparent")
        prov_frame.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(prov_frame, text="Active Provider:", width=120, anchor="w").pack(side="left")
        
        self.provider_var = ctk.StringVar(value=config.AI_PROVIDER)
        self.provider_menu = ctk.CTkOptionMenu(prov_frame, variable=self.provider_var, values=["gemini", "openai", "claude"])
        self.provider_menu.pack(side="left", fill="x", expand=True)

        # API Keys
        self.keys = {}
        
        def create_key_input(label, current_value):
            frame = ctk.CTkFrame(self, fg_color="transparent")
            frame.pack(fill="x", padx=20, pady=5)
            ctk.CTkLabel(frame, text=label, width=120, anchor="w").pack(side="left")
            entry = ctk.CTkEntry(frame, show="*")
            entry.insert(0, current_value)
            entry.pack(side="left", fill="x", expand=True)
            return entry
            
        self.keys["gemini"] = create_key_input("Gemini API Key:", config.GEMINI_API_KEY)
        self.keys["openai"] = create_key_input("OpenAI API Key:", config.OPENAI_API_KEY)
        self.keys["claude"] = create_key_input("Claude API Key:", config.CLAUDE_API_KEY)

        # Buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=30)
        
        save_btn = ctk.CTkButton(btn_frame, text="Save Settings", command=self._on_save, fg_color="#2ecc71", hover_color="#27ae60")
        save_btn.pack(side="right", padx=5)
        
        cancel_btn = ctk.CTkButton(btn_frame, text="Cancel", command=self.destroy, fg_color="#e74c3c", hover_color="#c0392b")
        cancel_btn.pack(side="right", padx=5)

    def _on_save(self):
        success = save_ai_settings(
            self.provider_var.get(),
            self.keys["gemini"].get().strip(),
            self.keys["openai"].get().strip(),
            self.keys["claude"].get().strip()
        )
        if success:
            messagebox.showinfo("Settings Saved", "AI Settings have been saved successfully.")
            self.destroy()
        else:
            messagebox.showerror("Error", "Failed to save settings.")

def open_ai_settings(parent):
    dialog = AISettingsDialog(parent)
    parent.wait_window(dialog)
