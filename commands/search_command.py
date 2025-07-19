from typing import List, Optional
from rich.console import Console
from rich.table import Table
import os
import sys
from ..utils.data_loading import load_and_prepare_omnifocus_data, query_prepared_data, get_latest_json_export_path

def handle_search(args):
    """
    Search tasks from the JSON export by project and/or search text.
    """
    file = getattr(args, 'file', None) or get_latest_json_export_path()
    data = load_and_prepare_omnifocus_data(file)
    if not data or not data.get("all_tasks"):
        print(f"No tasks found in {file}")
        return
    project = getattr(args, 'project', None)
    query = getattr(args, 'query', None)
    tasks = [t for t in data["all_tasks"] if (not project or t.get("projectId") == project)]
    if query:
        tasks = [t for t in tasks if query.lower() in t.get("name", "").lower() or query.lower() in t.get("note", "").lower()]
    for t in tasks:
        print(f"- {t.get('name')} (ID: {t.get('id')})")

    console = Console()
    if not tasks:
        print("No matching tasks found.")
        if project:
            print(f"Note: Search was limited to project '{project}'")
        return

    # Create a rich table for better formatting
    table = Table(show_header=True, header_style="bold")
    table.add_column("ID", style="cyan")
    table.add_column("Task", style="green")
    table.add_column("Due Date", style="yellow")
    table.add_column("Status", style="magenta")
    
    for task in tasks:
        status = "✓" if task.get("completed", False) or task.get("status", "").lower() == "completed" else " "
        due = task.get("dueDate") or task.get("due_date") or "-"
        table.add_row(
            str(task.get("id", "")),
            str(task.get("name", "")),
            str(due),
            status
        )
    
    console.print(table)
    print(f"\nFound {len(tasks)} matching tasks") 