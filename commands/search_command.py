from typing import List, Optional
from omnifocus_api import apple_script_client
from omnifocus_api.data_models import OmniFocusTask
from rich.console import Console
from rich.table import Table

def search_tasks(query: str, project: Optional[str] = None) -> List[OmniFocusTask]:
    """Search for tasks matching the query."""
    tasks = apple_script_client.fetch_tasks(project_name=project)
    if not tasks:
        return []
    
    query = query.lower()
    return [
        task for task in tasks
        if query in task.name.lower() or
           (task.note and query in task.note.lower())
    ]

def handle_search(args):
    """
    Search for tasks and display their IDs and details.
    """
    console = Console()
    query = args.query
    project = args.project

    print(f"Searching for tasks matching '{query}'...")
    matching_tasks = search_tasks(query, project)
    
    if not matching_tasks:
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
    
    for task in matching_tasks:
        status = "✓" if task.completed else " "
        due = task.due_date if task.due_date else "-"
        table.add_row(
            task.id,
            task.name,
            due,
            status
        )
    
    console.print(table)
    print(f"\nFound {len(matching_tasks)} matching tasks") 