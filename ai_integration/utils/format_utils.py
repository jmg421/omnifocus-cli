from typing import List
from ...omnifocus_api.data_models import OmniFocusTask
import datetime

def parse_date_string(date_str: str):
    """
    A stub function. Parse a user-supplied date string into something AppleScript can handle.
    For now, just return the same string if it's in "YYYY-MM-DD" format.
    Expand with dateparser or parsedatetime if desired.
    """
    # This is the simplest possible implementation
    # In a real implementation, you would:
    # 1. Use a library like dateparser to handle natural language dates
    # 2. Convert the parsed date to the format required by AppleScript
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

