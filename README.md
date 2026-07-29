# ⚡ Macro Recorder Pro — Complete Build Guide

> Built with Python VS Code Local Setup


## 🗺️ Build Roadmap

```
Week 1-2 ──► Phase 1: Recorder (capture mouse events)
Week 3   ──► Phase 2: Player (replay with timing)
Week 4   ──► Phase 3: Hotkeys + background mode
Week 5   ──► Phase 4: JSON save/load storage
Week 6-7 ──► Phase 5: Advanced (loops, delays, triggers)
Week 8-9 ──► Phase 6: UI editor + system tray
Week 10  ──► Package to .exe and final testing
```

---

## ⚡ Quick Start

```bash
# 1. Install dependencies
pip install pynput pywin32 keyboard pyinstaller pystray pillow

# 2. Run the tool
python main.py

# 3. Controls
F7  → Open Editor
F8  → Start recording
F9  → Stop & save
F10 → Replay
F11 → Abort playback
ESC → Exit
```

---

## 💡 Tech Stack

| Tool | Purpose |
|------|---------|
| Python 3.13 | Core language |
| pynput | Mouse & keyboard capture + replay |
| keyboard | Global hotkeys |
| pywin32 | Windows API access |
| tkinter | Built-in GUI (dark themed, zero extra install) |
| pystray | System tray icon |
| PyInstaller 6.x | Package to .exe |
| Inno Setup 6 | Windows installer (.exe setup) |
| VS Code (Portable) | Editor — no system install needed |
| GitHub Copilot (Opus 4.6) | AI pair programmer |
