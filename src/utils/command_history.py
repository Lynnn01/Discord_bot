from dataclasses import dataclass
from datetime import datetime
import discord
from typing import List, Dict

@dataclass
class CommandRecord:
    """บันทึกการใช้คำสั่ง"""
    user: discord.User
    action: str
    success: bool
    timestamp: datetime = datetime.now()

class CommandHistory:
    """จัดการประวัติการใช้คำสั่ง"""
    def __init__(self, max_size: int = 100):
        self.max_size = max_size
        self._history: List[CommandRecord] = []
        self._stats: Dict[str, int] = {
            "total": 0,
            "success": 0,
            "failed": 0
        }

    def add(self, user: discord.User, action: str, success: bool) -> None:
        """เพิ่มบันทึกใหม่"""
        record = CommandRecord(user, action, success)
        self._history.append(record)
        
        # Update stats
        self._stats["total"] += 1
        self._stats["success" if success else "failed"] += 1
        
        # Trim history if needed
        if len(self._history) > self.max_size:
            self._history.pop(0)

    def get_stats(self) -> Dict[str, int]:
        """รับสถิติการใช้คำสั่ง"""
        return self._stats.copy()

    def get_recent(self, count: int = 5) -> List[CommandRecord]:
        """รับประวัติล่าสุด"""
        return self._history[-count:]
