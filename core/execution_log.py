import json
import os
import time
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import List, Optional

import config

@dataclass
class LogEntry:
    timestamp: str
    action_index: int
    action_type: str
    action_details: str
    status: str  # "SUCCESS", "FAILED", "SKIPPED"
    duration_ms: float
    error_message: Optional[str] = None

class ExecutionLog:
    """Manages the execution log for a macro run."""

    def __init__(self, macro_name: str):
        self.macro_name = macro_name
        self.run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.entries: List[LogEntry] = []
        self.start_time = time.perf_counter()
        
        # Ensure log directory exists
        self.log_dir = os.path.join(config.BASE_DIR, "storage", "logs")
        os.makedirs(self.log_dir, exist_ok=True)
        self.log_file = os.path.join(self.log_dir, f"{self.macro_name}_{self.run_id}.json")

    def add_entry(self, index: int, action_type: str, details: str, status: str, duration: float, error: str = None):
        """Add a log entry for a single action."""
        entry = LogEntry(
            timestamp=datetime.now().isoformat(),
            action_index=index,
            action_type=action_type,
            action_details=details,
            status=status,
            duration_ms=round(duration * 1000, 2),
            error_message=error
        )
        self.entries.append(entry)

    def save(self):
        """Save the log to disk as JSON."""
        total_duration = time.perf_counter() - self.start_time
        
        data = {
            "macro_name": self.macro_name,
            "run_id": self.run_id,
            "start_time": self.entries[0].timestamp if self.entries else datetime.now().isoformat(),
            "end_time": datetime.now().isoformat(),
            "total_duration_sec": round(total_duration, 3),
            "total_actions": len(self.entries),
            "success_count": sum(1 for e in self.entries if e.status == "SUCCESS"),
            "fail_count": sum(1 for e in self.entries if e.status == "FAILED"),
            "entries": [asdict(e) for e in self.entries]
        }
        
        with open(self.log_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            
        print(f"[Player] Saved execution log to {self.log_file}")
