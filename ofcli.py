#!/usr/bin/env python3
import sys
import os
import typer
from typing import Optional, Literal, Any, Dict, List
from .utils import load_env_vars
from enum import Enum
from .omnifocus_api import test_evernote_export
from .omnifocus_api.apple_script_client import fetch_projects
import json

# Load environment variables
load_env_vars()

# -----------------------------------------------------------------------------
# START: query-export command logic (moved inline)
# -----------------------------------------------------------------------------

# Define status types
StatusType = Literal["active", "completed", "all"]

# Define query types
QueryType = Literal["projects", "tasks", "details", "folders"]

def _is_match(item: Dict[str, Any], status: StatusType) -> bool:
    """Check if an item matches the desired completion status."""
    if status == "all":
        return True
    is_completed = item.get("completed", False)
    if status == "active":
        return not is_completed
    if status == "completed":
        return is_completed
    return False # Should not happen with Literal types

def _find_items_recursive(
    data: Any,
    query_type: QueryType,
    status: StatusType,
    results: List[Dict[str, Any]], # Moved results before default args
    name_filter: Optional[str] = None,
    project_filter: Optional[str] = None, # Name of the project to filter tasks by
    folder_filter: Optional[str] = None,  # Name of the folder to filter projects by
    id_filter: Optional[str] = None,
    current_folder: Optional[str] = None,
    current_project: Optional[str] = None # Name of the current project context for tasks
):
    """Recursively search through the OmniFocus JSON structure."""
    if not isinstance(data, (dict, list)):
        return

    if isinstance(data, list):
        for item in data:
            _find_items_recursive(
                item, query_type, status, results, name_filter, project_filter,
                folder_filter, id_filter, current_folder, current_project
            )
        return

    item_id = data.get("id")
    item_name = data.get("name")
    item_type = data.get("type")

    new_current_folder = current_folder
    new_current_project = current_project

    if item_type == "Folder":
        new_current_folder = item_name
    elif item_type == "Project":
        new_current_project = item_name
        if data.get("folderId") is None: 
             new_current_folder = None

    match = False
    if query_type == "details" and id_filter and item_id == id_filter:
        match = True
    elif query_type == "folders" and item_type == "Folder":
        if status == "all" or (not name_filter or (item_name and name_filter.lower() in item_name.lower())):
            match = True 
    elif query_type == "projects" and item_type == "Project":
        if _is_match(data, status):
            if (not name_filter or (item_name and name_filter.lower() in item_name.lower())) and \
               (not folder_filter or folder_filter == new_current_folder):
                 match = True
    elif query_type == "tasks" and item_type == "Task":
        if (not project_filter or project_filter == new_current_project):
            if _is_match(data, status):
                if not name_filter or (item_name and name_filter.lower() in item_name.lower()):
                    match = True

    if match:
        context_to_add = {}
        if new_current_folder:
            context_to_add['folder'] = new_current_folder
        if new_current_project and item_type != "Project":
             context_to_add['project'] = new_current_project
        if context_to_add:
            data['_context'] = context_to_add
        results.append(data)
        if query_type == "details" and id_filter and item_id == id_filter:
            return 

    # Recurse into standard container keys
    for key in ["folders", "projects", "tasks", "children"]:
        if key in data and isinstance(data[key], list):
            _find_items_recursive(
                data[key], query_type, status, results, name_filter, project_filter,
                folder_filter, id_filter, new_current_folder, new_current_project
            )
            
    # Special handling for the structure: project.tasks[0].children
    if item_type == "Project" and "tasks" in data and isinstance(data["tasks"], list) and data["tasks"]:
         first_task_in_project = data["tasks"][0]
         # Ensure first_task_in_project is a dict and has children
         if isinstance(first_task_in_project, dict) and "children" in first_task_in_project and isinstance(first_task_in_project["children"], list):
              _find_items_recursive(
                   first_task_in_project["children"], query_type, status, results, name_filter, project_filter,
                   folder_filter, id_filter, new_current_folder, new_current_project # Pass project context
              )

def handle_query_export(args):
    json_file = args.json_file
    query_type = args.query_type
    status = args.status
    name_filter = args.name.lower() if args.name else None
    project_filter = args.project_name
    folder_filter = args.folder_name
    id_filter = args.item_id

    try:
        with open(json_file, 'r') as f:
            data_root = json.load(f)
    except FileNotFoundError:
        print(f"Error: File not found at {json_file}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {json_file}", file=sys.stderr)
        sys.exit(1)

    if not isinstance(data_root, dict) or "structure" not in data_root:
         print("Error: Unexpected JSON structure. Expected root object with a 'structure' key.", file=sys.stderr)
         sys.exit(1)

    found_items = []
    _find_items_recursive(
        data_root.get("structure", {}),
        query_type,
        status,
        found_items,
        name_filter=name_filter,
        project_filter=project_filter,
        folder_filter=folder_filter,
        id_filter=id_filter
    )
    
    if "topLevelProjects" in data_root.get("structure", {}):
        _find_items_recursive(
            data_root["structure"]["topLevelProjects"],
            query_type,
            status,
            found_items,
            name_filter=name_filter,
            project_filter=project_filter,
            folder_filter=folder_filter, 
            id_filter=id_filter
        )

    if not found_items:
        print("No items found matching the criteria.")
        return

    if query_type == "details":
        unique_items = {item.get('id', id(item)): item for item in found_items}.values() # Dedupe using object id as fallback
        print(json.dumps(list(unique_items)[0] if unique_items else {}, indent=2))
    elif query_type in ["projects", "tasks", "folders"]:
        unique_items_dict = {}
        for item in found_items:
            item_id_for_dedupe = item.get("id", id(item)) # Use object id as fallback key
            if item_id_for_dedupe not in unique_items_dict:
                unique_items_dict[item_id_for_dedupe] = item
        
        sorted_items = sorted(list(unique_items_dict.values()), key=lambda x: x.get("name", ""))

        print(f"Found {len(sorted_items)} unique {query_type}:")
        for item in sorted_items:
            name = item.get("name", "Unnamed Item")
            item_id = item.get("id", "No ID")
            line = f"- {name} (ID: {item_id})"
            context = item.get('_context')
            if context:
                if context.get('folder') and query_type != 'folders':
                     line += f" [Folder: {context['folder']}]"
                if context.get('project') and query_type == 'tasks':
                     line += f" [Project: {context['project']}]"
            print(line)
    else:
         print(f"Unknown query type: {query_type}", file=sys.stderr)

# -----------------------------------------------------------------------------
# END: query-export command logic
# -----------------------------------------------------------------------------

class CleanupMode(str, Enum):
    all = "all"
    inbox = "inbox"
    flagged = "flagged"
    overdue = "overdue"

# Create app instance
app = typer.Typer(
    name="ofcli",
    help="OmniFocus CLI - Manage tasks, projects, and priorities with AI.",
    no_args_is_help=True,
)

# Use direct imports from existing directories
from .commands.add_command import handle_add
from .commands.list_command import handle_list
from .commands.complete_command import handle_complete
from .commands.prioritize_command import handle_prioritize
from .commands.delegation_command import handle_delegation
from .commands.audit_command import handle_audit
from .commands.calendar_command import handle_calendar
from .commands.imessage_command import handle_imessage
from .commands.scan_command import handle_scan
from .commands.cleanup_command import handle_cleanup
from .commands.search_command import handle_search

@app.command("add")
def add(
    title: str = typer.Option(..., "--title", "-t", help="Title of the new task."),
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Project to place the task in."),
    note: Optional[str] = typer.Option(None, "--note", "-n", help="Optional note."),
    due: Optional[str] = typer.Option(None, "--due", "-d", help="Due date/time (natural language or YYYY-MM-DD)."),
):
    """Add a new task or project to OmniFocus."""
    args = type('Args', (), {
        'title': title,
        'project': project,
        'note': note,
        'due': due
    })
    handle_add(args)

@app.command("list")
def list_tasks(
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Filter tasks by project."),
    search: Optional[str] = typer.Option(None, "--search", "-s", help="Search for tasks containing text."),
    json_output: bool = typer.Option(False, "--json", help="Output in JSON format."),
):
    """List tasks or projects from OmniFocus."""
    args = type('Args', (), {
        'project': project,
        'search': search,
        'json': json_output
    })
    handle_list(args)

@app.command("complete")
def complete(
    task_ids: list[str] = typer.Argument(..., help="One or more task IDs to complete."),
):
    """Mark tasks as complete in OmniFocus."""
    args = type('Args', (), {
        'task_id': task_ids
    })
    handle_complete(args)

@app.command("prioritize")
def prioritize(
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Project to focus on."),
    limit: int = typer.Option(10, "--limit", "-l", help="Number of tasks to include in AI prioritization."),
    finance: bool = typer.Option(False, "--finance", "-f", help="Focus on organizing and simplifying finance-related tasks."),
    deduplicate: bool = typer.Option(False, "--deduplicate", "-d", help="Find and suggest consolidation of duplicate tasks."),
):
    """Use AI to prioritize tasks in OmniFocus."""
    args = type('Args', (), {
        'project': project,
        'limit': limit,
        'finance': finance,
        'deduplicate': deduplicate
    })
    handle_prioritize(args)

@app.command("delegate")
def delegate(
    task_id: str = typer.Argument(..., help="Task ID to delegate."),
    to: str = typer.Option(..., "--to", help="Email or name of the person."),
    method: str = typer.Option("email", "--method", help="Delegate via email or other method."),
):
    """Delegate tasks to someone else."""
    args = type('Args', (), {
        'task_id': task_id,
        'to': to,
        'method': method
    })
    handle_delegation(args)

@app.command("audit")
def audit(
    limit: int = typer.Option(100, "--limit", "-l", help="Maximum number of tasks to analyze."),
    export: bool = typer.Option(False, "--export", "-e", help="Export reference material to a file for Evernote import."),
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Focus on a specific project."),
    generate_script: bool = typer.Option(False, "--generate-script", "-s", help="Generate an AppleScript for bulk cleanup operations."),
):
    """Analyze and categorize OmniFocus tasks to help clean up and reorganize your database."""
    args = type('Args', (), {
        'limit': limit,
        'export': export,
        'project': project,
        'generate_script': generate_script
    })
    handle_audit(args)

@app.command("calendar")
def calendar(
    calendar_url: str = typer.Option(..., "--url", "-u", help="URL of the iCal calendar subscription"),
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Focus on a specific project"),
):
    """Sync with iCal calendar to verify task reality."""
    args = type('Args', (), {
        'calendar_url': calendar_url,
        'project': project
    })
    handle_calendar(args)

@app.command("imessage")
def imessage(
    contact: str = typer.Option(..., "--contact", "-c", help="Name or identifier of the contact to sync"),
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Project to add tasks to"),
):
    """Sync iMessage conversations with OmniFocus tasks."""
    args = type('Args', (), {
        'contact': contact,
        'project': project
    })
    handle_imessage(args)

@app.command("scan")
def scan(
    days: int = typer.Option(7, "--days", "-d", help="Number of days of messages to scan"),
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Project to add tasks to"),
):
    """Scan recent messages for action items and interactively add them to OmniFocus."""
    args = type('Args', (), {
        'days': days,
        'project': project
    })
    handle_scan(args)

@app.command("cleanup")
def cleanup(
    mode: CleanupMode = typer.Option(CleanupMode.all, "--mode", "-m", help="What to clean up: all, inbox, flagged, or overdue"),
    batch: int = typer.Option(10, "--batch", "-b", help="Number of tasks to review before asking to continue"),
):
    """Interactively clean up overdue, flagged, and inbox items."""
    args = type('Args', (), {
        'mode': mode.value,
        'batch': batch
    })
    handle_cleanup(args)

@app.command("test-evernote")
def test_evernote():
    """Test Evernote integration."""
    if test_evernote_export():
        print("✓ Successfully tested Evernote integration")
    else:
        print("✗ Failed to test Evernote integration")

@app.command("search")
def search(
    query: str = typer.Argument(..., help="Search term to find in task names and notes."),
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Limit search to a specific project."),
):
    """Search for tasks and display their IDs."""
    args = type('Args', (), {
        'query': query,
        'project': project
    })
    handle_search(args)

@app.command("list-projects")
def list_projects():
    """List all project names in OmniFocus (fast)."""
    projects = fetch_projects()
    if not projects:
        print("No projects found or error fetching projects.")
        return
    print("OmniFocus Projects:")
    for p in projects:
        print(f"- {p}")

# Define query types and status types for Typer choices
QueryTypeChoice = Enum("QueryTypeChoice", {t: t for t in QueryType.__args__})
StatusTypeChoice = Enum("StatusTypeChoice", {s: s for s in StatusType.__args__})

@app.command("query-export")
def query_export(
    query_type: QueryTypeChoice = typer.Option(..., "--query-type", "-q", help="Type of item to query (projects, tasks, details, folders).", case_sensitive=False),
    status: StatusTypeChoice = typer.Option(StatusTypeChoice.active, "--status", help="Filter by status (active, completed, all).", case_sensitive=False),
    name: Optional[str] = typer.Option(None, "--name", "-n", help="Filter items by name (case-insensitive substring match)."),
    project_name: Optional[str] = typer.Option(None, "--project-name", "-p", help="Filter tasks by project name."),
    folder_name: Optional[str] = typer.Option(None, "--folder-name", "-f", help="Filter projects by folder name."),
    item_id: Optional[str] = typer.Option(None, "--id", help="Get details for a specific item ID."),
    json_file: str = typer.Option("data/omnifocus_export.json", "--file", help="Path to the OmniFocus JSON export file.")
):
    """Query the OmniFocus JSON export file (data/omnifocus_export.json)."""
    if query_type == QueryTypeChoice.details and not item_id:
        print("Error: --id is required when using --query-type details", file=sys.stderr)
        raise typer.Exit(code=1)
    if query_type == QueryTypeChoice.tasks and project_name is None and name is None:
         print("Warning: Querying all tasks without specific project or name filter might return many results.", file=sys.stderr)

    args = type('Args', (), {
        'query_type': query_type.value,
        'status': status.value,
        'name': name,
        'project_name': project_name,
        'folder_name': folder_name,
        'item_id': item_id,
        'json_file': json_file
    })
    handle_query_export(args)

if __name__ == "__main__":
    app() 