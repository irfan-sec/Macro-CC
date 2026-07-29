"""
Macro Recorder Pro — Entry Point

Launches the full GUI window with system tray icon and global hotkeys.

Hotkeys:
  F7  → Open macro editor / show window
  F8  → Start recording
  F9  → Stop recording & save
  F10 → Replay last macro
  F11 → Abort current replay
  Ctrl+Shift+Q → Exit
"""

import os
import sys
import ctypes
import threading
import traceback
from tkinter import messagebox

from core.recorder import Recorder
from core.player import Player
from core.hook_manager import HookManager
from storage.macro_store import MacroStore
from features.proxy_manager import ProxyManager
import config


def global_exception_handler(exc_type, exc_value, exc_traceback):
    """Catch all unhandled exceptions and show them in a GUI dialog."""
    # Don't show dialog for KeyboardInterrupt
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
        
    error_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    print(f"FATAL ERROR:\n{error_msg}", file=sys.stderr)
    
    try:
        messagebox.showerror(
            "Application Error",
            f"An unexpected error occurred.\n\n{exc_type.__name__}: {exc_value}\n\nCheck the console log for full traceback."
        )
    except Exception:
        # If Tkinter is totally dead, just pass
        pass

class App:
    def __init__(self):
        # ── Admin check ──
        try:
            if ctypes.windll.shell32.IsUserAnAdmin():
                print("✅ Running as Administrator")
            else:
                print("⚠️  WARNING: Not running as Administrator")
                print("   Some apps may not accept mouse input injection.")
                print("   If hotkeys or clicks don't work, relaunch as Admin.")
        except Exception as e:
            print(f"[App] Error: {e}")

        # ── DPI awareness (must be set before any UI) ──
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception as e:
            print(f"[App Error] {e}")
            try:
                ctypes.windll.user32.SetProcessDPIAware()
            except Exception as e:
                print(f"[App Error] {e}")

        # ── Core components ──
        self.recorder = Recorder()
        self.player   = Player()
        self.hooks    = HookManager()
        self.store    = MacroStore(config.MACROS_DIR)

        self.player.speed_multiplier = config.DEFAULT_SPEED
        self.current_macro_name      = config.DEFAULT_MACRO_NAME

        # ── Proxy / network manager ──
        self.proxy_manager = ProxyManager()

        # ── GUI window (created later in run()) ──
        self.window = None

        # ── System tray icon ──
        from ui.tray_icon import TrayIcon
        self.tray = TrayIcon(self)
        self.tray.start()

        # ── Register hotkeys ──
        self._setup_hotkeys()

    def _setup_hotkeys(self):
        self.hooks.register(config.HOTKEY_START_RECORDING, self.start_recording, "Start recording")
        self.hooks.register(config.HOTKEY_STOP_RECORDING,  self.stop_recording,  "Stop & save")
        self.hooks.register(config.HOTKEY_REPLAY,          self.replay,          "Replay macro")
        self.hooks.register(config.HOTKEY_ABORT,           self.abort,           "Abort replay")
        self.hooks.register(config.HOTKEY_OPEN_EDITOR,     self.open_editor,     "Open editor")
        self.hooks.register(config.HOTKEY_EXIT,            self.quit,            "Exit app")

    # ── Actions ──────────────────────────────────────────────────

    def start_recording(self):
        if self.window:
            try:
                self.window.after(0, self.window._on_record)
            except Exception as e:
                print(f"[App Error] {e}")
            return
        if self.player.is_playing:
            print("[App] Can't record while playing")
            return
        if self.recorder.is_recording:
            print("[App] Already recording")
            return
        self.recorder.start()
        try:
            self.tray.set_state("recording")
        except Exception as e:
            print(f"[App Error] {e}")

    def stop_recording(self):
        if self.window:
            try:
                self.window.after(0, self.window._on_stop)
            except Exception as e:
                print(f"[App Error] {e}")
            return
        if not self.recorder.is_recording:
            print("[App] Not recording")
            return
        events = self.recorder.stop()
        if events:
            self.store.save(self.current_macro_name, events)
            print(f"[App] Saved {len(events)} events")
        try:
            self.tray.set_state("idle")
        except Exception as e:
            print(f"[App Error] {e}")

    def replay(self):
        if self.window:
            try:
                self.window.after(0, self.window._on_play)
            except Exception as e:
                print(f"[App Error] {e}")
            return
        if self.recorder.is_recording:
            print("[App] Stop recording first")
            return
        if self.player.is_playing:
            print("[App] Already playing")
            return

        # ── Apply proxy env vars before replay ──
        self._apply_proxy_env()

        events = self.store.load(self.current_macro_name)
        if not events:
            print(f"[App] No macro '{self.current_macro_name}' found")
            return

        def on_each_loop_done(loop_num: int):
            """Called after every single macro loop completes."""
            if hasattr(self, 'proxy_manager') and self.proxy_manager.mode != "direct":
                self.proxy_manager.rotate()
                new_proxy = self.proxy_manager.current_proxy

                # Update system environment proxies immediately
                current = self.proxy_manager.get_current()
                if current:
                    os.environ['HTTP_PROXY']  = current.get('http', '')
                    os.environ['HTTPS_PROXY'] = current.get('https', '')
                    os.environ['http_proxy']  = current.get('http', '')
                    os.environ['https_proxy'] = current.get('https', '')

                # Update status bar in UI if window exists
                if self.window:
                    new_ip = f"{new_proxy.host}:{new_proxy.port}" if new_proxy else "Unknown"
                    try:
                        self.window.after(0, lambda ip=new_ip:
                            self.window.update_network_status(f"🔄 Rotated → {ip}"))
                    except Exception as e:
                        print(f"[App Error] {e}")

                print(f"[App] ✅ Macro loop {loop_num} done — IP rotated")

        def _on_done():
            print("[App] ✅ All loops complete")
            try:
                self.tray.set_state("idle")
            except Exception as e:
                print(f"[App Error] {e}")
            if self.window:
                try:
                    self.window.after(0, self.window._playback_finished)
                except Exception as e:
                    print(f"[App Error] {e}")

        self.player.replay(
            events,
            loops=config.DEFAULT_LOOPS,
            on_each_loop_done=on_each_loop_done,
            on_done=_on_done,
        )
        try:
            self.tray.set_state("playing")
        except Exception as e:
            print(f"[App Error] {e}")

    def abort(self):
        if self.window:
            try:
                self.window.after(0, self.window._stop_playback)
            except Exception as e:
                print(f"[App Error] {e}")
            return
        if self.player.is_playing:
            self.player.abort()
            try:
                self.tray.set_state("idle")
            except Exception as e:
                print(f"[App Error] {e}")
        else:
            print("[App] Nothing to abort")

    def open_editor(self):
        """Show/raise the main window."""
        if self.window:
            try:
                self.window.after(0, self._raise_window)
            except Exception as e:
                print(f"[App Error] {e}")

    def _raise_window(self):
        """Bring the window to front (must run on main thread)."""
        if self.window:
            self.window.deiconify()
            self.window.lift()
            self.window.focus_force()

    def _apply_proxy_env(self):
        """Set HTTP_PROXY/HTTPS_PROXY env vars based on current proxy mode."""
        current = self.proxy_manager.get_current()
        if current:
            os.environ["HTTP_PROXY"] = current.get("http", "")
            os.environ["HTTPS_PROXY"] = current.get("https", "")
        else:
            os.environ.pop("HTTP_PROXY", None)
            os.environ.pop("HTTPS_PROXY", None)
        # Rotate if per_macro mode
        if self.proxy_manager.rotation_mode == "per_macro":
            self.proxy_manager.rotate()

    def quit(self):
        print("\n[App] Shutting down...")
        self.player.abort()
        try:
            self.recorder.stop()
        except Exception as e:
            print(f"[App Error] {e}")
        self.hooks.unregister_all()
        
        # Stop background services
        if hasattr(self, 'proxy_manager'):
            self.proxy_manager.stop_auto_rotation()
            
        if self.tray:
            self.tray.stop()
            
        if self.window:
            # Stop scheduler
            if hasattr(self.window, '_scheduler'):
                self.window._scheduler.stop()
            try:
                self.window.after(0, self.window.destroy)
            except Exception as e:
                print(f"[App Error] {e}")
        os._exit(0)

    def run(self):
        """Launch the main GUI window (blocks on tkinter mainloop)."""
        from ui.main_window import MacroRecorderWindow

        self.window = MacroRecorderWindow(app=self)

        # Handle window close → minimize to tray instead of exit
        self.window.protocol("WM_DELETE_WINDOW", self._on_window_close)

        print("=" * 50)
        print(f"  >  {config.APP_NAME} v{config.APP_VERSION}")
        print("=" * 50)
        print(f"  {config.HOTKEY_OPEN_EDITOR.upper():15} -> Show window")
        print(f"  {config.HOTKEY_START_RECORDING.upper():15} -> Start recording")
        print(f"  {config.HOTKEY_STOP_RECORDING.upper():15} -> Stop & save")
        print(f"  {config.HOTKEY_REPLAY.upper():15} -> Replay")
        print(f"  {config.HOTKEY_ABORT.upper():15} -> Abort replay")
        print(f"  {config.HOTKEY_EXIT.upper():15} -> Exit")
        print("=" * 50)

        # Hook global exceptions
        sys.excepthook = global_exception_handler
        self.window.report_callback_exception = global_exception_handler

        self.window.mainloop()

    def _on_window_close(self):
        """When user clicks X, minimize to tray instead of quitting."""
        if self.window:
            self.window.withdraw()


if __name__ == "__main__":
    App().run()
