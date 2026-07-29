"""Central configuration — change settings here, not scattered in code."""

import os
import sys

# ── Hotkeys ──────────────────────────────────────────────────
# Global hotkeys that work even when the app is not focused
HOTKEY_START_RECORDING  = "f8"
HOTKEY_STOP_RECORDING   = "f9"
HOTKEY_REPLAY           = "f10"
HOTKEY_ABORT            = "f11"
HOTKEY_OPEN_EDITOR      = "f7"
HOTKEY_EXIT             = "ctrl+shift+q"

# ── Storage ───────────────────────────────────────────────────
# Paths that work both when running as .py and as frozen .exe
BASE_DIR = (
    os.path.dirname(sys.executable)
    if getattr(sys, 'frozen', False)
    else os.path.dirname(os.path.abspath(__file__))
)
MACROS_DIR = os.path.join(BASE_DIR, "storage", "macros")
DEFAULT_MACRO_NAME = "macro1"

# ── Playback ──────────────────────────────────────────────────
# Default speed multiplier (1.0 = normal, 0.5 = 2x faster, 2.0 = 2x slower)
DEFAULT_SPEED = 1.0
# How many times to replay by default
DEFAULT_LOOPS = 1

# ── Recorder Throttle ─────────────────────────────────────────
# Move events are skipped if BOTH thresholds are below these values
MOVE_DISTANCE_THRESHOLD = 5      # pixels
MOVE_TIME_THRESHOLD     = 0.05   # seconds (50ms)

# ── App Info ──────────────────────────────────────────────────
APP_NAME    = "Macro Recorder Pro"
APP_VERSION = "2.0.0"

# ── AI Integration ────────────────────────────────────────────
AI_PROVIDER = "gemini"  # 'gemini', 'openai', or 'claude'
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
CLAUDE_API_KEY = os.environ.get("CLAUDE_API_KEY", "")
SHOW_ONBOARDING = True

# ── Persistent Settings Load/Save ──────────────────────────────
import json
SETTINGS_FILE = os.path.join(BASE_DIR, "storage", "settings.json")

def load_settings():
    global AI_PROVIDER, GEMINI_API_KEY, OPENAI_API_KEY, CLAUDE_API_KEY, SHOW_ONBOARDING
    global HOTKEY_START_RECORDING, HOTKEY_STOP_RECORDING, HOTKEY_REPLAY, HOTKEY_ABORT
    
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                
            AI_PROVIDER = data.get("AI_PROVIDER", AI_PROVIDER)
            GEMINI_API_KEY = data.get("GEMINI_API_KEY", GEMINI_API_KEY)
            OPENAI_API_KEY = data.get("OPENAI_API_KEY", OPENAI_API_KEY)
            CLAUDE_API_KEY = data.get("CLAUDE_API_KEY", CLAUDE_API_KEY)
            SHOW_ONBOARDING = data.get("SHOW_ONBOARDING", SHOW_ONBOARDING)
            
            HOTKEY_START_RECORDING = data.get("HOTKEY_START_RECORDING", HOTKEY_START_RECORDING)
            HOTKEY_STOP_RECORDING = data.get("HOTKEY_STOP_RECORDING", HOTKEY_STOP_RECORDING)
            HOTKEY_REPLAY = data.get("HOTKEY_REPLAY", HOTKEY_REPLAY)
            HOTKEY_ABORT = data.get("HOTKEY_ABORT", HOTKEY_ABORT)
        except Exception as e:
            print(f"[Config] Failed to load settings: {e}")

def save_settings():
    os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
    data = {
        "AI_PROVIDER": AI_PROVIDER,
        "GEMINI_API_KEY": GEMINI_API_KEY,
        "OPENAI_API_KEY": OPENAI_API_KEY,
        "CLAUDE_API_KEY": CLAUDE_API_KEY,
        "SHOW_ONBOARDING": SHOW_ONBOARDING,
        "HOTKEY_START_RECORDING": HOTKEY_START_RECORDING,
        "HOTKEY_STOP_RECORDING": HOTKEY_STOP_RECORDING,
        "HOTKEY_REPLAY": HOTKEY_REPLAY,
        "HOTKEY_ABORT": HOTKEY_ABORT
    }
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"[Config] Failed to save settings: {e}")

load_settings()
