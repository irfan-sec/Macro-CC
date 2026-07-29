import tkinter as tk
from tkinter import filedialog
import customtkinter as ctk
import os
import threading
from PIL import Image

from ui.theme import BG_PRIMARY, BG_SECONDARY, ACCENT, TEXT_COLOR, TEXT_DIM
from features.ai_agent import AIAgent
from ui.ai_approval_dialog import open_ai_approval

class AIChatPanel(ctk.CTkFrame):
    """Full-screen chat interface for interacting with the multimodal AI Agent."""

    def __init__(self, master, app_main, **kwargs):
        super().__init__(master, fg_color=BG_PRIMARY, **kwargs)
        self.app_main = app_main
        self.ai_agent = AIAgent()
        self._current_image_path = None

        # --- Top Header ---
        header = ctk.CTkFrame(self, fg_color=BG_SECONDARY, corner_radius=8)
        header.pack(fill="x", pady=(0, 10))
        
        ctk.CTkLabel(header, text="✨ AI Assistant", font=("Segoe UI", 16, "bold"), text_color=TEXT_COLOR).pack(side="left", padx=15, pady=10)
        ctk.CTkLabel(header, text="Powered by Gemini, OpenAI, Claude", font=("Segoe UI", 12), text_color=TEXT_DIM).pack(side="right", padx=15)

        # --- Chat History (Scrollable) ---
        self.chat_history = ctk.CTkScrollableFrame(self, fg_color=BG_SECONDARY, corner_radius=8)
        self.chat_history.pack(fill="both", expand=True, pady=(0, 10))
        
        # Initial greeting
        self._add_message("Assistant", "Hello! I can write macros for you. Tell me what you want to do, or attach a screenshot to show me what you're looking at.")

        # --- Input Area ---
        input_frame = ctk.CTkFrame(self, fg_color=BG_SECONDARY, corner_radius=8)
        input_frame.pack(fill="x")
        
        # Image Preview Area (hidden by default)
        self.img_preview_frame = ctk.CTkFrame(input_frame, fg_color="transparent")
        self.img_preview_label = ctk.CTkLabel(self.img_preview_frame, text="")
        self.img_preview_label.pack(side="left", padx=10, pady=5)
        
        remove_img_btn = ctk.CTkButton(self.img_preview_frame, text="✖ Remove", width=60, fg_color="#e74c3c", hover_color="#c0392b", command=self._remove_image)
        remove_img_btn.pack(side="left", padx=5)

        # Bottom row: Attach, Entry, Send
        bottom_row = ctk.CTkFrame(input_frame, fg_color="transparent")
        bottom_row.pack(fill="x", padx=10, pady=10)
        
        attach_btn = ctk.CTkButton(bottom_row, text="📎 Attach Image", width=120, fg_color=BG_PRIMARY, hover_color="#333", command=self._attach_image)
        attach_btn.pack(side="left", padx=(0, 10))
        
        screenshot_btn = ctk.CTkButton(bottom_row, text="📸 Live Screenshot", width=120, fg_color=BG_PRIMARY, hover_color="#333", command=self._take_live_screenshot)
        screenshot_btn.pack(side="left", padx=(0, 10))
        
        self.entry = ctk.CTkEntry(bottom_row, placeholder_text="Type your command here...", font=("Segoe UI", 14))
        self.entry.pack(side="left", fill="x", expand=True)
        self.entry.bind("<Return>", lambda e: self._send_message())
        
        self.send_btn = ctk.CTkButton(bottom_row, text="Send 🚀", width=80, fg_color=ACCENT, command=self._send_message)
        self.send_btn.pack(side="right", padx=(10, 0))

    def _add_message(self, sender: str, text: str, image_path: str = None, events: list = None):
        """Add a message block to the chat history."""
        msg_frame = ctk.CTkFrame(self.chat_history, fg_color=BG_PRIMARY if sender=="User" else "transparent")
        msg_frame.pack(fill="x", padx=10, pady=5)
        
        header_color = ACCENT if sender == "User" else "#e67e22" # Orange for AI
        ctk.CTkLabel(msg_frame, text=sender, font=("Segoe UI", 12, "bold"), text_color=header_color).pack(anchor="w", padx=10, pady=(5, 0))
        
        if image_path:
            ctk.CTkLabel(msg_frame, text=f"[Attached Image: {os.path.basename(image_path)}]", text_color=TEXT_DIM).pack(anchor="w", padx=10)
            
        ctk.CTkLabel(msg_frame, text=text, font=("Segoe UI", 14), justify="left", wraplength=600).pack(anchor="w", padx=10, pady=(2, 5))
        
        if events:
            # Add a button to preview the generated macro
            def on_preview():
                approved = open_ai_approval(self.app_main, events)
                if approved:
                    for ev in approved:
                        self.app_main._loaded_events.append(ev.to_dict())
                    self.app_main._refresh_action_list()
                    self.app_main._save_current_silently()
                    self._add_message("System", "✅ Macro successfully imported to the current project.")
                    
            preview_btn = ctk.CTkButton(msg_frame, text="View & Apply Generated Macro", fg_color="#2ecc71", hover_color="#27ae60", command=on_preview)
            preview_btn.pack(anchor="w", padx=10, pady=(0, 10))
            
        # Scroll to bottom
        self.chat_history._parent_canvas.yview_moveto(1.0)

    def _attach_image(self):
        filepath = filedialog.askopenfilename(title="Select Screenshot", filetypes=[("Image Files", "*.png *.jpg *.jpeg")])
        if filepath:
            self._set_preview_image(filepath)
            
    def _take_live_screenshot(self):
        self.app_main.iconify() # Hide window to take screenshot
        self.after(500, self._capture_screen) # wait 500ms for window to hide
        
    def _capture_screen(self):
        import pyautogui
        # Save temp screenshot
        temp_path = os.path.join(os.path.dirname(__file__), "..", "storage", "temp_screenshot.png")
        os.makedirs(os.path.dirname(temp_path), exist_ok=True)
        pyautogui.screenshot(temp_path)
        self.app_main.deiconify() # Show window again
        self._set_preview_image(temp_path)

    def _set_preview_image(self, filepath: str):
        self._current_image_path = filepath
        self.img_preview_label.configure(text=f"Attached: {os.path.basename(filepath)}")
        self.img_preview_frame.pack(fill="x", padx=10, pady=(10, 0))

    def _remove_image(self):
        self._current_image_path = None
        self.img_preview_frame.pack_forget()

    def _send_message(self):
        text = self.entry.get().strip()
        if not text and not self._current_image_path:
            return
            
        self.entry.delete(0, tk.END)
        self.send_btn.configure(state="disabled", text="Thinking...")
        
        img_path = self._current_image_path
        self._remove_image()
        
        self._add_message("User", text, image_path=img_path)
        
        # Run AI generation in background
        threading.Thread(target=self._generate_async, args=(text, img_path), daemon=True).start()
        
    def _generate_async(self, command: str, image_path: str):
        try:
            events = self.ai_agent.generate_macro(command, image_path=image_path)
            if events:
                self.after(0, lambda: self._add_message("Assistant", "I have generated a macro based on your request. Click the button below to review it.", events=events))
            else:
                self.after(0, lambda: self._add_message("Assistant", "I couldn't generate any events for that request."))
        except Exception as e:
            self.after(0, lambda: self._add_message("System", f"❌ Error communicating with AI: {e}"))
        finally:
            self.after(0, lambda: self.send_btn.configure(state="normal", text="Send 🚀"))
