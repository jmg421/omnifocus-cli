"""
Data models representing OmniFocus objects (tasks, projects, etc.).
"""

from dataclasses import dataclass
from typing import Optional

@dataclass
class OmniFocusTask:
    id: str
    name: str
    note: str
    completed: bool
    due_date: Optional[str] = None
    project: Optional[str] = None

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "note": self.note,
            "completed": self.completed,
            "due_date": self.due_date,
            "project": self.project
        }

