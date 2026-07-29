import threading
import time
import json
import os
from datetime import datetime

import config
from core.player import Player

class ScheduledTask:
    def __init__(self, macro_name: str, hour: int, minute: int, enabled: bool = True):
        self.macro_name = macro_name
        self.hour = hour
        self.minute = minute
        self.enabled = enabled
        self.last_run_date = None

    def to_dict(self):
        return {
            "macro_name": self.macro_name,
            "hour": self.hour,
            "minute": self.minute,
            "enabled": self.enabled,
            "last_run_date": self.last_run_date
        }
        
    @classmethod
    def from_dict(cls, data):
        task = cls(
            macro_name=data["macro_name"],
            hour=data["hour"],
            minute=data["minute"],
            enabled=data.get("enabled", True)
        )
        task.last_run_date = data.get("last_run_date")
        return task

class MacroScheduler:
    """Background service that runs scheduled macros."""
    
    def __init__(self, store, player: Player):
        self.store = store
        self.player = player
        self.tasks: list[ScheduledTask] = []
        self._running = False
        
        self.save_file = os.path.join(config.BASE_DIR, "storage", "schedules.json")
        self.load()
        
    def add_task(self, macro_name: str, hour: int, minute: int):
        task = ScheduledTask(macro_name, hour, minute)
        self.tasks.append(task)
        self.save()
        
    def remove_task(self, index: int):
        if 0 <= index < len(self.tasks):
            self.tasks.pop(index)
            self.save()
            
    def toggle_task(self, index: int, enabled: bool):
        if 0 <= index < len(self.tasks):
            self.tasks[index].enabled = enabled
            self.save()

    def start(self):
        """Start the background scheduler thread."""
        if self._running:
            return
        self._running = True
        threading.Thread(target=self._run_loop, daemon=True).start()
        print("[Scheduler] Started background service")

    def stop(self):
        self._running = False

    def _run_loop(self):
        while self._running:
            now = datetime.now()
            today_str = now.strftime("%Y-%m-%d")
            
            for task in self.tasks:
                if not task.enabled:
                    continue
                    
                # Check if it's time to run
                if now.hour == task.hour and now.minute == task.minute:
                    # Prevent running multiple times in the same minute
                    if task.last_run_date != today_str:
                        print(f"[Scheduler] Triggering scheduled macro: {task.macro_name}")
                        task.last_run_date = today_str
                        self.save()
                        
                        # Load and play
                        macro_data = self.store.load(task.macro_name)
                        if macro_data:
                            self.player.replay(macro_data["events"], loops=1)
            
            time.sleep(30) # Poll every 30 seconds

    def save(self):
        with open(self.save_file, "w", encoding="utf-8") as f:
            json.dump([t.to_dict() for t in self.tasks], f, indent=2)

    def load(self):
        if not os.path.exists(self.save_file):
            return
        try:
            with open(self.save_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.tasks = [ScheduledTask.from_dict(d) for d in data]
        except Exception as e:
            print(f"[Scheduler] Error loading schedules: {e}")
