from typing import List
from ...omnifocus_api.data_models import OmniFocusTask
import datetime
import dateparser

def parse_date_string(date_str: str):
    """
    Parse a user-supplied date string into AppleScript-compatible format.
    Handles:
      - YYYY-MM-DD (e.g., 2025-07-13)
      - Natural language (e.g., 'tomorrow', 'next Friday')
    Returns:
      - 'Month DD, YYYY HH:MM:SS' (e.g., 'July 13, 2025 00:00:00')
      - None if parsing fails
    """
    if not date_str or not isinstance(date_str, str):
        return None
    # Try YYYY-MM-DD first
    import re
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", date_str.strip())
    if m:
        from datetime import datetime
        try:
            dt = datetime.strptime(date_str.strip(), "%Y-%m-%d")
            return dt.strftime("%B %d, %Y 00:00:00")
        except Exception:
            pass
    # Fallback to dateparser
    dt = dateparser.parse(date_str)
    if dt:
        return dt.strftime("%B %d, %Y %H:%M:%S")
    # If all fails, return original string (AppleScript may error)
    return date_str


def format_task_list(tasks: List[OmniFocusTask]) -> str:
    """Format a list of tasks for display."""
    if not tasks:
        return "No tasks found."
    
    output = []
    for task in tasks:
        due_str = f" (Due: {task.due_date})" if task.due_date else ""
        project_str = f" [Project: {task.project}]" if hasattr(task, 'project') and task.project else ""
        output.append(f"{task.id}: {task.name}{due_str}{project_str}")
    
    return "\n".join(output)


def format_priority_recommendations(lines: List[str]) -> str:
    """Format priority recommendations from the AI."""
    if not lines:
        return "No priority recommendations available."
    
    return "\n".join(lines)

