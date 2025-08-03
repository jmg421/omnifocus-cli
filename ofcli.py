#!/usr/bin/env python3
import sys
import os
import typer
from typing import Optional, Any, Dict, List
from datetime import datetime, date, timedelta # Added for date parsing and timedelta
# Add thefuzz for fuzzy string matching
from thefuzz import fuzz, process

import warnings
# Attempt to import NotOpenSSLWarning specifically, if it fails, pass for broader urllib3 warning suppression.
try:
    from urllib3.exceptions import NotOpenSSLWarning
    warnings.filterwarnings('ignore', category=NotOpenSSLWarning)
except ImportError:
    # Fallback if NotOpenSSLWarning is not found (e.g. older urllib3 or different structure)
    # This might suppress more urllib3 warnings than intended, but should catch the SSL one.
    warnings.filterwarnings('ignore', message=".*OpenSSL 1.1.1+.*")

from .utils.config import load_env_vars
from enum import Enum
from .omnifocus_api import test_evernote_export
import json
import csv # Add csv import
import glob
from .utils.data_loading import load_and_prepare_omnifocus_data, query_prepared_data, get_latest_json_export_path

import subprocess
from rich.console import Console
from pathlib import Path

# === Default Paths ===
def get_latest_json_export_path():
    """Return path to a fresh export, creating one if necessary."""
    try:
        from .utils.ensure_export import ensure_fresh_export
        return ensure_fresh_export(int(os.getenv("OF_EXPORT_MAX_AGE", "1800")))
    except Exception as e:
        # First try data/exports directory
        export_files = glob.glob('data/exports/*/*/omnifocus-export-*.json')
        if export_files:
            export_files.sort(key=os.path.getmtime, reverse=True)
            return export_files[0]
        
        # Fallback to Desktop directory if no exports in data/exports
        desktop_files = glob.glob(os.path.expanduser('~/Desktop/omnifocus-export-*.json'))
        if not desktop_files:
            print(f"Warning: ensure_fresh_export failed ({e}) and no export found.", file=sys.stderr)
            return None
        desktop_files.sort(key=os.path.getmtime, reverse=True)
        return desktop_files[0]

# Load environment variables
load_env_vars()

# --- Date Helper Functions (Module Level) ---
def parse_cli_date(date_str: Optional[str]) -> Optional[date]: # Already module level in query_prepared_data, move here if used more widely.
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        print(f"Warning: Could not parse CLI date string: {date_str}", file=sys.stderr)
        return None

def get_item_date(item_date_val: Optional[str]) -> Optional[date]:
    if not item_date_val: # Handles None or empty string
        return None
    try:
        # Attempt to parse ISO format datetime string and take date part
        return datetime.fromisoformat(item_date_val.replace('Z', '+00:00')).date()
    except (ValueError, TypeError):
        try:
            # Fallback for simple YYYY-MM-DD if already in that format
            return datetime.strptime(item_date_val, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            # print(f"Warning: Could not parse item date value: {item_date_val}", file=sys.stderr)
            return None
# --- End Date Helper Functions ---

# NEW function to load and prepare data (rewritten for OmniJS full_dump v1.2 structure)
def load_and_prepare_omnifocus_data(json_file_path: str) -> Dict[str, Any]:
    """
    Loads OmniFocus data from the JSON export (produced by OmniJS export script)
    and prepares it for querying. 
    Handles nested structure of folders, projects, and tasks.
    Returns a dictionary containing 'all_tasks', 'projects_map', 'folders_map', 'tags_map'.
    """
    try:
        with open(json_file_path, 'r') as f:
            raw_data = json.load(f)
    except FileNotFoundError:
        print(f"Error: File not found at {json_file_path}", file=sys.stderr)
        return {}
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {json_file_path}", file=sys.stderr)
        return {}

    # Initialize collections
    tasks_dict: Dict[str, Dict[str, Any]] = {}
    projects_dict: Dict[str, Dict[str, Any]] = {}
    folders_dict: Dict[str, Dict[str, Any]] = {}

    def process_task(task_data: Dict[str, Any], project_id: Optional[str] = None, parent_task_id: Optional[str] = None):
        if not task_data or not isinstance(task_data, dict) or not task_data.get('id'):
            return
        task_id = task_data['id']
        task_copy = task_data.copy()
        task_copy.setdefault('name', f'Unnamed Task {task_id}')
        if project_id:
            task_copy['projectId'] = project_id
        if parent_task_id:
            task_copy['parentId'] = parent_task_id
        task_copy['_source'] = 'project' if project_id else 'inbox'
        tasks_dict[task_id] = task_copy
        # Recursively process children if present
        children = task_data.get("children", [])
        if isinstance(children, list):
            for child_task_data in children:
                process_task(child_task_data, project_id, parent_task_id=task_id)

    def process_project(project_data: Dict[str, Any], folder_id: Optional[str] = None):
        if not project_data or not isinstance(project_data, dict) or not project_data.get('id'):
            return
        project_id = project_data['id']
        project_copy = project_data.copy()
        project_copy.setdefault('name', f'Unnamed Project {project_id}')
        if folder_id:
            project_copy['folderId'] = folder_id
        projects_dict[project_id] = project_copy
        # Process tasks within this project
        project_tasks_list = project_data.get("tasks", [])
        if isinstance(project_tasks_list, list):
            for task_data in project_tasks_list:
                process_task(task_data, project_id=project_id)

    def process_folder(folder_data: Dict[str, Any], parent_folder_id: Optional[str] = None):
        if not folder_data or not isinstance(folder_data, dict) or not folder_data.get('id'):
            return
        folder_id = folder_data['id']
        folder_copy = folder_data.copy()
        folder_copy.setdefault('name', f'Unnamed Folder {folder_id}')
        if parent_folder_id:
            folder_copy['parentFolderID'] = parent_folder_id
        folders_dict[folder_id] = folder_copy
        # No subfolders or projects in this export, but keep for future compatibility

    # --- Updated processing for new export structure ---
    # Process all folders
    folders = raw_data.get("folders", {})
    if isinstance(folders, dict):
        for folder in folders.values():
            process_folder(folder)
    # Process all projects
    projects = raw_data.get("projects", {})
    if isinstance(projects, dict):
        for project in projects.values():
            process_project(project, folder_id=project.get("folderID"))
    # Process top-level tasks (present in new export schema)
    top_level_tasks = raw_data.get("tasks", [])
    if isinstance(top_level_tasks, list):
        for task_data in top_level_tasks:
            proj_id = task_data.get("projectId") if isinstance(task_data, dict) else None
            process_task(task_data, project_id=proj_id)

    # Process inbox tasks if provided separately
    inbox_tasks = raw_data.get("inboxTasks", [])
    if isinstance(inbox_tasks, list):
        for task_data in inbox_tasks:
            process_task(task_data)  # project_id=None indicates inbox

    return {
        "all_tasks": list(tasks_dict.values()),
        "projects_map": projects_dict,
        "folders_map": folders_dict,
        "tags_map": raw_data.get("tags", {}),
    }

# NEW Querying Function
def query_prepared_data(
    prepared_data: Dict[str, Any],
    query_type: str, # "tasks", "projects", "folders"
    item_id_filter: Optional[str] = None,
    name_filter: Optional[str] = None,
    project_id_filter: Optional[str] = None, # For tasks
    folder_id_filter: Optional[str] = None,   # For projects
    status_filter: Optional[str] = None,
    due_before_filter: Optional[str] = None,
    due_after_filter: Optional[str] = None,
    defer_before_filter: Optional[str] = None,
    defer_after_filter: Optional[str] = None,
    completed_before_filter: Optional[str] = None,
    completed_after_filter: Optional[str] = None,
    tag_ids_all_filter: Optional[List[str]] = None, # Expecting a list of IDs
    tag_ids_any_filter: Optional[List[str]] = None  # Expecting a list of IDs
) -> List[Dict[str, Any]]:

    all_tasks: List[Dict[str, Any]] = prepared_data.get("all_tasks", [])
    projects_map: Dict[str, Dict[str, Any]] = prepared_data.get("projects_map", {})
    folders_map: Dict[str, Dict[str, Any]] = prepared_data.get("folders_map", {})
    
    results: List[Dict[str, Any]] = []

    # Parse CLI date filters once
    due_before_date = parse_cli_date(due_before_filter)
    due_after_date = parse_cli_date(due_after_filter)
    defer_before_date = parse_cli_date(defer_before_filter)
    defer_after_date = parse_cli_date(defer_after_filter)
    completed_before_date = parse_cli_date(completed_before_filter)
    completed_after_date = parse_cli_date(completed_after_filter)

    # Convert tag filter lists to sets for efficient lookup
    tag_ids_all_set = set(tag_ids_all_filter) if tag_ids_all_filter else set()
    tag_ids_any_set = set(tag_ids_any_filter) if tag_ids_any_filter else set()

    # --- Item ID Filter (takes precedence) ---
    if item_id_filter:
        # Search across all primary collections if an ID is provided
        if item_id_filter in projects_map:
            if query_type == "projects" or query_type == "all_items": 
                results.append(projects_map[item_id_filter])
                return results 
        if item_id_filter in folders_map:
            if query_type == "folders" or query_type == "all_items": 
                results.append(folders_map[item_id_filter])
                return results
        for task in all_tasks:
            if task.get("id") == item_id_filter:
                if query_type == "tasks" or query_type == "all_items":
                    results.append(task)
                    return results 
        return results 
    # --- End Item ID Filter ---

    if query_type == "tasks":
        for item in all_tasks: # Changed from 'task' to generic 'item' for consistency
            match = True
            # Name filter
            if name_filter and not (name_filter.lower() in item.get("name", "").lower()):
                match = False; continue
            # Project ID filter
            if project_id_filter and item.get("projectId") != project_id_filter:
                match = False; continue
            # Status filter
            if status_filter and not (item.get("status", "").lower() == status_filter.lower()):
                match = False; continue
            
            # Date filters for tasks
            item_due_date = get_item_date(item.get("dueDate"))
            if due_before_date and (not item_due_date or item_due_date >= due_before_date):
                match = False; continue
            if due_after_date and (not item_due_date or item_due_date <= due_after_date):
                match = False; continue
            
            item_defer_date = get_item_date(item.get("deferDate"))
            if defer_before_date and (not item_defer_date or item_defer_date >= defer_before_date):
                match = False; continue
            if defer_after_date and (not item_defer_date or item_defer_date <= defer_after_date):
                match = False; continue

            item_completed_date = get_item_date(item.get("completedDate")) # Corrected from item.get("completionDate") which is in OmniJS but not consistently in my current Python item structure
            if completed_before_date and (not item_completed_date or item_completed_date >= completed_before_date):
                match = False; continue
            if completed_after_date and (not item_completed_date or item_completed_date <= completed_after_date):
                match = False; continue

            # Tag filters for tasks
            item_tag_ids_set = set(item.get("tagIds", []))
            if tag_ids_all_set and not tag_ids_all_set.issubset(item_tag_ids_set):
                match = False; continue
            if tag_ids_any_set and tag_ids_any_set.isdisjoint(item_tag_ids_set):
                match = False; continue
            
            if match:
                results.append(item)

    elif query_type == "projects":
        for project_id, item in projects_map.items(): # Changed from 'project_data' to generic 'item'
            match = True
            # Name filter
            if name_filter and not (name_filter.lower() in item.get("name", "").lower()):
                match = False; continue
            # Folder ID filter
            if folder_id_filter and item.get("folderId") != folder_id_filter:
                match = False; continue
            # Status filter
            if status_filter and not (item.get("status", "").lower() == status_filter.lower()):
                match = False; continue
            
            # Date filters for projects (similar to tasks)
            item_due_date = get_item_date(item.get("dueDate"))
            # ... (add similar due, defer, completed date filter logic as for tasks if applicable to projects) ...
            # Example for project due date:
            if due_before_date and (not item_due_date or item_due_date >= due_before_date):
                 match = False; continue
            if due_after_date and (not item_due_date or item_due_date <= due_after_date):
                 match = False; continue
            # Note: Projects in your JSON have dueDate, deferDate, completionDate. They don't have tagIds.

            if match:
                results.append(item)

    elif query_type == "folders":
        for folder_id, item in folders_map.items(): # Changed from 'folder_data' to generic 'item'
            match = True
            # Name filter
            if name_filter and not (name_filter.lower() in item.get("name", "").lower()):
                match = False; continue
            # Status filter (Folders in your JSON have a status field from OmniJS)
            if status_filter and not (item.get("status", "").lower() == status_filter.lower()):
                match = False; continue
            # Note: Folders in your JSON don't have dates or tags.

            if match:
                results.append(item)
    
    return results

# Definition for CleanupMode Enum (restored)
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
from .commands.add_command import handle_add, handle_add_detailed_task, handle_create_project
from .commands.list_command import handle_list, handle_list_live_tasks_in_project, handle_list_live_projects
from .commands.complete_command import handle_complete
from .commands.prioritize_command import prioritize as prioritize_command
from .commands.delegation_command import handle_delegation
from .commands.audit_command import handle_audit
from .commands.calendar_command import handle_calendar, handle_add_calendar_event
from .commands.imessage_command import handle_imessage
from .commands.scan_command import handle_scan
from .commands.cleanup_command import handle_cleanup
from .commands.search_command import handle_search
from .commands.merge_command import handle_merge_projects
from .commands.delete_command import handle_delete_project, handle_delete_task
from .commands.icalbuddy_integration import handle_icalbuddy_test, handle_icalbuddy_verify, handle_icalbuddy_conflicts
from .commands.applescript_calendar_integration import handle_applescript_calendar_test, handle_applescript_calendar_verify, handle_applescript_calendar_conflicts, handle_applescript_calendar_events
from .commands.next_command import handle_next
from .commands.archive_command import handle_archive_completed

@app.command("add")
def add(
    title: str = typer.Option(..., "--title", "-t", help="Title of the new task."),
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Project to place the task in."),
    note: Optional[str] = typer.Option(None, "--note", "-n", help="Optional note."),
    due: Optional[str] = typer.Option(None, "--due", "-d", help="Due date/time (natural language or YYYY-MM-DD)."),
    duration: Optional[int] = typer.Option(None, "--duration", "-D", help="Estimated duration in minutes."),
):
    """Quick add a new task to OmniFocus (alias for add-task)."""
    args = type('Args', (), {
        'title': title,
        'folder_name': None,
        'project_name': project,
        'note': note,
        'tags': None,
        'due_date': due,
        'defer_date': None,
        'recurrence_rule': None,
        'duration': duration
    })
    handle_add_detailed_task(args)

@app.command("add-task")
def add_detailed_task_command(
    title: str = typer.Option(..., "--title", "-t", help="Title of the new task."),
    folder_name: Optional[str] = typer.Option(None, "--folder", "-f", help="Folder to place the task in (cannot be used with --project)."),
    project_name: Optional[str] = typer.Option(None, "--project", "-p", help="Project to place the task in (cannot be used with --folder)."),
    note: Optional[str] = typer.Option(None, "--note", "-n", help="Optional note for the task."),
    tags: Optional[str] = typer.Option(None, "--tags", help="Comma-separated list of tags to assign to the task."),
    due_date: Optional[str] = typer.Option(None, "--due", help="Due date (natural language or YYYY-MM-DD). Needed for some recurrence rules."),
    defer_date: Optional[str] = typer.Option(None, "--defer", help="Defer date (natural language or YYYY-MM-DD)."),
    recurrence_rule: Optional[str] = typer.Option(None, "--recurrence", "-r", help='Recurrence rule string (e.g., "FREQ=MONTHLY;INTERVAL=1").'),
    duration: Optional[int] = typer.Option(None, "--duration", "-D", help="Estimated duration in minutes."),
):
    """Adds a new task to OmniFocus with detailed options including recurrence, folder/project placement, tags, and duration."""
    if project_name and folder_name:
        print("Error: --project and --folder cannot be used together", file=sys.stderr)
        raise typer.Exit(code=1)
    args = type('Args', (), {
        'title': title,
        'folder_name': folder_name,
        'project_name': project_name,
        'note': note,
        'tags': tags,
        'due_date': due_date,
        'defer_date': defer_date,
        'recurrence_rule': recurrence_rule,
        'duration': duration
    })
    handle_add_detailed_task(args)

@app.command("list")
def list_tasks(
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Filter tasks by project."),
    search: Optional[str] = typer.Option(None, "--search", "-s", help="Search for tasks containing text."),
    json_output: bool = typer.Option(False, "--json", help="Output in JSON format."),
    file: Optional[str] = typer.Option(get_latest_json_export_path(), "--file", help="Path to the OmniFocus JSON export file.")
):
    """List tasks or projects from OmniFocus export file."""
    data = load_and_prepare_omnifocus_data(file)
    tasks = data.get('all_tasks', [])
    # Filter by project if specified
    if project:
        tasks = [t for t in tasks if t.get('projectId') and data['projects_map'].get(t['projectId'], {}).get('name') == project]
    # Filter by search if specified
    if search:
        tasks = [t for t in tasks if search.lower() in t.get('name', '').lower() or search.lower() in t.get('note', '').lower()]
    if json_output:
        import json
        print(json.dumps(tasks, indent=2))
    else:
        for t in tasks:
            print(f"- {t.get('name')} (Project: {data['projects_map'].get(t.get('projectId'), {}).get('name', 'None')}){' [FLAGGED]' if t.get('flagged') else ''}{' [DUE: ' + t.get('dueDate') + ']' if t.get('dueDate') else ''}")

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
    file: Optional[str] = typer.Option(get_latest_json_export_path(), "--file", help="Path to the OmniFocus JSON export file (defaults to latest export).")
):
    """Use AI to prioritize tasks in OmniFocus."""
    prioritize_command(file=file, project=project, limit=limit, finance=finance, deduplicate=deduplicate)

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

@app.command("icalbuddy-test")
def icalbuddy_test():
    """Test icalBuddy integration and permissions."""
    args = type('Args', (), {})
    handle_icalbuddy_test(args)

@app.command("icalbuddy-verify")
def icalbuddy_verify(
    task_name: str = typer.Option(..., "--task", "-t", help="Name of the task to verify"),
    notes: Optional[str] = typer.Option(None, "--notes", "-n", help="Optional task notes for verification"),
):
    """Verify if a task corresponds to real calendar events."""
    args = type('Args', (), {
        'task_name': task_name,
        'notes': notes
    })
    handle_icalbuddy_verify(args)

@app.command("icalbuddy-conflicts")
def icalbuddy_conflicts(
    start_time: str = typer.Option(..., "--start", "-s", help="Start time (YYYY-MM-DD HH:MM)"),
    end_time: str = typer.Option(..., "--end", "-e", help="End time (YYYY-MM-DD HH:MM)"),
):
    """Check for scheduling conflicts in a time range."""
    args = type('Args', (), {
        'start_time': start_time,
        'end_time': end_time
    })
    handle_icalbuddy_conflicts(args)

@app.command("calendar-test")
def calendar_test():
    """Test AppleScript calendar integration (works without special permissions)."""
    args = type('Args', (), {})
    handle_applescript_calendar_test(args)

@app.command("calendar-verify")
def calendar_verify(
    task_name: str = typer.Option(..., "--task", "-t", help="Name of the task to verify"),
    notes: Optional[str] = typer.Option(None, "--notes", "-n", help="Optional task notes for verification"),
):
    """Verify if a task corresponds to real calendar events using AppleScript."""
    args = type('Args', (), {
        'task_name': task_name,
        'notes': notes
    })
    handle_applescript_calendar_verify(args)

@app.command("calendar-conflicts")
def calendar_conflicts(
    start_time: str = typer.Option(..., "--start", "-s", help="Start time (YYYY-MM-DD HH:MM)"),
    end_time: str = typer.Option(..., "--end", "-e", help="End time (YYYY-MM-DD HH:MM)"),
):
    """Check for scheduling conflicts in a time range using AppleScript."""
    args = type('Args', (), {
        'start_time': start_time,
        'end_time': end_time
    })
    handle_applescript_calendar_conflicts(args)

@app.command("calendar-events")
def calendar_events(
    start_time: str = typer.Option(..., "--start", "-s", help="Start time (YYYY-MM-DD HH:MM)"),
    end_time: str = typer.Option(..., "--end", "-e", help="End time (YYYY-MM-DD HH:MM)"),
):
    """Get all calendar events in a time range using AppleScript."""
    args = type('Args', (), {
        'start_time': start_time,
        'end_time': end_time
    })
    handle_applescript_calendar_events(args)

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

# ---------------------------------------------------------------------------
# Compatibility shim
# ---------------------------------------------------------------------------

# Older versions of this script referenced a helper called
# `fetch_projects_from_json()` to quickly extract the project list from a JSON
# export.  That helper was replaced by the more robust
# `load_and_prepare_omnifocus_data()` pipeline, but some stale installations or
# documentation may still invoke it.  To avoid a hard failure (NameError) we
# provide a thin wrapper that delegates to the new implementation.


def fetch_projects_from_json(json_file_path: str):  # noqa: N802  pylint: disable=invalid-name
    """Return a mapping of project_id -> project_dict from an OmniFocus JSON export.

    This keeps backward compatibility with scripts or docs that still expect a
    `fetch_projects_from_json()` helper.  Internally we simply load the full
    structured export and return its `projects_map`.
    """
    prepared = load_and_prepare_omnifocus_data(json_file_path)
    return prepared.get("projects_map", {})

@app.command("list-projects")
def list_projects(
    file: Optional[str] = typer.Option(get_latest_json_export_path(), "--file", help="Path to the OmniFocus JSON export file.")
):
    """List all project names in OmniFocus (fast)."""
    # Use the compatibility helper so that we only have one code-path for
    # fetching projects.  Note: the helper returns a dict mapping id->project.
    projects_map = fetch_projects_from_json(file)
    if not projects_map:
        print("No projects found or error fetching projects.")
        return
    print("OmniFocus Projects:")
    for project_id, project in projects_map.items():
        print(f"- {project.get('name', 'Unnamed Project')} (ID: {project_id})")

@app.command("merge-projects")
def merge_projects_command(
    source_id: str = typer.Option(..., "--source-id", "-s", help="ID of the project to merge tasks from."),
    target_id: str = typer.Option(..., "--target-id", "-t", help="ID of the project to merge tasks into."),
    delete_source: bool = typer.Option(False, "--delete-source", "-d", help="Delete the source project after merging.")
):
    """Merge tasks from a source project to a target project in OmniFocus."""
    args = type('Args', (), {
        'source_id': source_id,
        'target_id': target_id,
        'delete_source': delete_source
    })
    handle_merge_projects(args)

@app.command("create-project")
def create_project_command(
    title: str = typer.Option(..., "--title", "-t", help="Title of the new project."),
    folder_name: Optional[str] = typer.Option(None, "--folder", "-f", help="Optional folder to create the project in.")
):
    """Creates a new project, optionally within a specified folder."""
    handle_create_project(title=title, folder_name=folder_name)

@app.command("delete-project")
def delete_project_command(
    project_id: str = typer.Option(..., "--id", help="ID of the project to delete.")
):
    """Delete a project from OmniFocus using its ID."""
    args = type('Args', (), {
        'project_id': project_id
    })
    handle_delete_project(args)

@app.command("delete-task")
def delete_task_command(
    task_id: str = typer.Option(..., "--id", help="ID of the task to delete.")
):
    """Delete a task from OmniFocus using its ID."""
    args = type('Args', (), {
        'task_id': task_id
    })
    handle_delete_task(args)

@app.command("query")
def query_command(
    query: str = typer.Argument("", help="Task ID or search string to look up in task names/notes. If blank, lists all tasks."),
    json_file: str = typer.Option(
        None,
        "--file",
        help="Path to the OmniFocus JSON or CSV export file.",
    ),
    input_format: str = typer.Option(
        "json",
        "--input-format",
        help="Format of the input file ('json' or 'csv'). Default: 'json'."
    ),
    query_type: str = typer.Option(
        "tasks",
        "--query-type", "-q",
        help="Type of item to query (tasks, projects, folders). Case sensitive for value, not for option name. Default: 'tasks'."
    ),
    output_format: str = typer.Option(
        "text",
        "--output-format",
        help="Output format (text, json). Default: 'text'."
    ),
    # Keep advanced filters for compatibility
    name: Optional[str] = typer.Option(None, "--name", "-n", help="Filter by name (substring match)." ),
    project_id: Optional[str] = typer.Option(None, "--project-id", "-p", help="For tasks: filter by project ID."),
    folder_id: Optional[str] = typer.Option(None, "--folder-id", "-f", help="For projects: filter by folder ID."),
    status: Optional[str] = typer.Option(None, "--status", "-s", help="Filter by status (e.g., Active, Completed). Case insensitive."),
    due_before: Optional[str] = typer.Option(None, "--due-before", help="Filter by due date before YYYY-MM-DD."),
    due_after: Optional[str] = typer.Option(None, "--due-after", help="Filter by due date after YYYY-MM-DD."),
    defer_before: Optional[str] = typer.Option(None, "--defer-before", help="Filter by defer date before YYYY-MM-DD."),
    defer_after: Optional[str] = typer.Option(None, "--defer-after", help="Filter by defer date after YYYY-MM-DD."),
    completed_before: Optional[str] = typer.Option(None, "--completed-before", help="Filter by completed date before YYYY-MM-DD."),
    completed_after: Optional[str] = typer.Option(None, "--completed-after", help="Filter by completed date after YYYY-MM-DD."),
    tag_ids: Optional[str] = typer.Option(None, "--tag-ids", help="Comma-separated Tag IDs (item must have ALL). Tasks only."),
    tag_ids_any: Optional[str] = typer.Option(None, "--tag-ids-any", help="Comma-separated Tag IDs (item must have ANY). Tasks only."),
):
    """
    Query OmniFocus data by Task ID or search string (default: tasks, text output).
    If the query matches a Task/Project/Folder ID, returns that item. Otherwise, does a substring search in names/notes.
    """
    if not json_file:
        # Try to get the latest export path
        latest_path = get_latest_json_export_path()
        if latest_path and os.path.exists(latest_path):
            json_file = latest_path
        else:
            print("Error: No OmniFocus export file found. Run 'ofcli.py ingest' to create one.", file=sys.stderr)
            raise typer.Exit(code=1)

    if input_format.lower() == "csv":
        print(f"Loading data from CSV: {json_file}", file=sys.stderr)
        prepared_data = load_and_prepare_data_from_csv(json_file)
        if "_csv_parser_warnings" in prepared_data:
            print(f"CSV Parser Warning: {prepared_data['_csv_parser_warnings']}", file=sys.stderr)
    elif input_format.lower() == "json":
        print(f"Loading data from JSON: {json_file}", file=sys.stderr)
        prepared_data = load_and_prepare_omnifocus_data(json_file)
    else:
        print(f"Error: Unsupported input format '{input_format}'. Use 'json' or 'csv'.", file=sys.stderr)
        raise typer.Exit(code=1)

    if not prepared_data or not prepared_data.get("all_tasks"):
        if not prepared_data.get("projects_map") and (query_type == "projects" or query_type == "folders"):
            print("No data loaded or data is empty.", file=sys.stderr)
            return
        elif query_type == "tasks" and not prepared_data.get("all_tasks"):
            print("No task data loaded or task data is empty.", file=sys.stderr)
            return

    # Parse tag_ids and tag_ids_any from comma-separated strings to lists
    tag_ids_all_list = [tag.strip() for tag in tag_ids.split(',')] if tag_ids else None
    tag_ids_any_list = [tag.strip() for tag in tag_ids_any.split(',')] if tag_ids_any else None

    def find_best_match(query, prepared_data):
        """Return ('project', project_dict) if query matches a project by ID or name, ('task', task_dict) if exact match, or ('tasks', [task_dict, ...]) for substring matches."""
        # Try project by ID
        project = prepared_data.get('projects_map', {}).get(query)
        if project:
            return 'project', project
        # Try project by name (case-insensitive, exact or substring)
        for proj in prepared_data.get('projects_map', {}).values():
            if proj.get('name', '').lower() == query.lower():
                return 'project', proj
        for proj in prepared_data.get('projects_map', {}).values():
            if query.lower() in proj.get('name', '').lower():
                return 'project', proj
        # Try task by ID
        for t in prepared_data.get('all_tasks', []):
            if t.get('id') == query:
                return 'task', t
        # Try task by name (case-insensitive, exact)
        for t in prepared_data.get('all_tasks', []):
            if t.get('name', '').lower() == query.lower():
                return 'task', t
        # Substring match: collect all tasks where name or notes contain query
        matches = []
        for t in prepared_data.get('all_tasks', []):
            name = t.get('name', '').lower()
            notes = (t.get('notes') or t.get('note') or '').lower()
            if query.lower() in name or query.lower() in notes:
                matches.append(t)
        if matches:
            return 'tasks', matches
        return None, None

    # Determine if query is an ID (exact match) or a search string
    item_id = None
    search_name = name
    best_type, best_item = (None, None)
    if query:
        best_type, best_item = find_best_match(query, prepared_data)
        if best_type == 'project':
            # Show project and its tasks, regardless of query_type
            project = best_item
            project_id = project.get('id')
            project_tasks = get_tasks_for_project(project_id, prepared_data)
            if output_format.lower() == 'json':
                print(json.dumps({"project": project, "tasks": project_tasks}, indent=2))
            else:
                pretty_print_item(project, prepared_data)
                if project_tasks:
                    print(f"\nTasks in project '{project.get('name')}' ({len(project_tasks)}):\n" + "-"*60)
                    for t in project_tasks:
                        pretty_print_item(t, prepared_data)
                else:
                    print("\nNo tasks found in this project.")
            return
        elif best_type == 'task':
            item_id = best_item.get('id')
            search_name = None
        elif best_type == 'tasks':
            matches = best_item
            if output_format.lower() == 'json':
                print(json.dumps(matches, indent=2))
            else:
                print(f"Found {len(matches)} matching tasks:")
                for t in matches:
                    pretty_print_item(t, prepared_data)
            return

    results = query_prepared_data(
        prepared_data,
        query_type=query_type,
        item_id_filter=item_id,
        name_filter=search_name,
        project_id_filter=project_id,
        folder_id_filter=folder_id,
        status_filter=status,
        due_before_filter=due_before,
        due_after_filter=due_after,
        defer_before_filter=defer_before,
        defer_after_filter=defer_after,
        completed_before_filter=completed_before,
        completed_after_filter=completed_after,
        tag_ids_all_filter=tag_ids_all_list,
        tag_ids_any_filter=tag_ids_any_list
    )
    if not results:
        print("No items found matching the criteria.")
        return

    if output_format.lower() == "json":
        print(json.dumps(results, indent=2))
    elif output_format.lower() == "text":
        if len(results) == 1 and (item_id or search_name):
            pretty_print_item(results[0], prepared_data)
        else:
            print(f"Found {len(results)} {query_type}:")
            for item in results:
                item_name = item.get("name", "Unnamed Item")
                item_id_disp = item.get("id", "No ID")
                actual_item_type = item.get("type", query_type)
                if query_type.endswith('s') and actual_item_type == query_type:
                    item_type_disp = actual_item_type[:-1].capitalize()
                else:
                    item_type_disp = actual_item_type.capitalize()
                line = f"- Type: {item_type_disp}, Name: {item_name}, ID: {item_id_disp}"
                if item.get("status"):
                    line += f", Status: {item.get('status')}"
                if actual_item_type.lower() in ["task", "action", "project"]:
                    if item.get("dueDate"):
                        line += f", Due: {get_item_date(item.get('dueDate'))}"
                    if item.get("deferDate"):
                        line += f", Defer: {get_item_date(item.get('deferDate'))}"
                    if item.get("completedDate"):
                        line += f", Completed: {get_item_date(item.get('completedDate'))}"
                if actual_item_type.lower() in ["task", "action"]:
                    if item.get("projectId"):
                        project_id_val = item['projectId']
                        project_info = prepared_data.get("projects_map", {}).get(project_id_val, {})
                        project_name = project_info.get("name", "Unknown Project")
                        line += f" [Project: {project_name} (ID: {project_id_val})]"
                        folder_id_val_for_project = project_info.get("folderId")
                        if folder_id_val_for_project:
                            folder_info = prepared_data.get("folders_map", {}).get(folder_id_val_for_project, {})
                            folder_name = folder_info.get("name", "Unknown Folder")
                            line += f" (In Folder: {folder_name} (ID: {folder_id_val_for_project}))"
                    if item.get("parentId"):
                        line += f" [ParentTaskID: {item.get('parentId')}]"
                    if item.get("tagIds"):
                        line += f" [TagIDs: {', '.join(item.get('tagIds', []))}]"
                elif actual_item_type.lower() == "project":
                    if item.get("folderId"):
                        folder_id_val = item['folderId']
                        folder_info = prepared_data.get("folders_map", {}).get(folder_id_val, {})
                        folder_name = folder_info.get("name", "Unknown Folder")
                        line += f" [Folder: {folder_name} (ID: {folder_id_val})]"
                print(line)
    else:
        print(f"Error: Unknown output format '{output_format}'.", file=sys.stderr)
        raise typer.Exit(code=1)

@app.command("list-live-tasks")
def list_live_tasks_command(
    project_name: str = typer.Option(..., "--project-name", "-p", help="Name of the project to list tasks from."),
    file: Optional[str] = typer.Option(get_latest_json_export_path(), "--file", help="Path to the OmniFocus JSON export file.")
):
    # Implementation should use the file argument to load data
    pass  # Replace with actual logic

@app.command("list-live-projects")
def list_live_projects_command(
    json_output: bool = typer.Option(False, "--json", help="Output in JSON format.")
):
    """List live projects directly from OmniFocus via AppleScript.

    The command is intentionally fast and bypasses any JSON export file.  When
    the `--json` flag is supplied we emit structured JSON; otherwise a
    human-friendly plain-text table is printed.  The heavy lifting is done in
    `commands.list_command.handle_list_live_projects` so we simply forward the
    option.
    """
    from .commands.list_command import handle_list_live_projects  # Imported lazily to avoid any Typer circulars

    args = type("Args", (), {"json_output": json_output})
    handle_list_live_projects(args)

@app.command("add-calendar-event")
def add_calendar_event_command(
    title: str = typer.Option(..., "--title", "-t", help="Title of the calendar event."),
    start_date: str = typer.Option(..., "--start-date", help="Start date/time (YYYY-MM-DD or YYYY-MM-DD HH:MM)."),
    end_date: str = typer.Option(..., "--end-date", help="End date/time (YYYY-MM-DD or YYYY-MM-DD HH:MM)."),
    notes: Optional[str] = typer.Option(None, "--notes", "-n", help="Optional notes for the event."),
    calendar_name: Optional[str] = typer.Option(None, "--calendar", "-c", help="Name of the calendar to add the event to (e.g., 'Home', 'Work'). Defaults to 'Family Member 1' (iCloud) if not specified.")
):
    """Add a new event to Apple Calendar."""
    # Default to 'Family Member 1' if calendar_name is not provided
    if not calendar_name:
        calendar_name = "Family Member 1"
    args = type('Args', (), {
        'title': title,
        'start_date': start_date,
        'end_date': end_date,
        'notes': notes,
        'calendar_name': calendar_name
    })
    handle_add_calendar_event(args)

# --- NEW CSV Parsing Functionality ---
def parse_csv_task_id(task_id_str: str) -> tuple[Optional[str], ...]:
    """Parses dot-separated Task ID into a tuple of its parts."""
    return tuple(task_id_str.split('.'))

def get_parent_csv_task_id_str(task_id_parts: tuple[Optional[str], ...]) -> Optional[str]:
    """Gets the parent Task ID string from a parsed Task ID tuple."""
    if len(task_id_parts) > 1:
        return '.'.join(task_id_parts[:-1])
    return None

def parse_csv_date_to_iso(date_str: Optional[str]) -> Optional[str]:
    if not date_str or date_str.strip() == "":
        return None
    try:
        # Common OmniFocus CSV date format: "2024-08-07 12:00:00 +0000"
        # Sometimes it might be just YYYY-MM-DD
        if len(date_str) > 10: # Likely includes time and timezone
             # Attempt to parse common OF CSV format, then to ISO
            dt_obj = datetime.strptime(date_str.split(" +")[0], "%Y-%m-%d %H:%M:%S")
            return dt_obj.isoformat() + "Z" # Assume UTC if timezone was +0000
        else: # Assume YYYY-MM-DD
            dt_obj = datetime.strptime(date_str, "%Y-%m-%d")
            # return dt_obj.isoformat() # Return just date for YYYY-MM-DD
            return dt_obj.isoformat() + "T00:00:00Z" # Return as full ISO string at start of day UTC

    except ValueError:
        # print(f"Warning: Could not parse date string '{date_str}' from CSV. Leaving as is or None.", file=sys.stderr)
        return None # Or return original string if preferred: date_str

def load_and_prepare_data_from_csv(csv_file_path: str) -> Dict[str, Any]:
    """
    Loads OmniFocus data from a CSV export and prepares it for querying.
    Returns a dictionary containing 'all_tasks', 'projects_map', 'folders_map' (initially empty), 'tags_map'.
    """
    raw_tasks_from_csv: List[Dict[str, Any]] = []
    projects_dict: Dict[str, Dict[str, Any]] = {}
    # Folders are not explicitly in this CSV structure, so folders_map will be empty for now.
    # We might infer them later if project names have path-like structures.
    folders_dict: Dict[str, Dict[str, Any]] = {} 
    all_tags_found: Dict[str, Dict[str, Any]] = {} # To store unique tags encountered

    header_map = {
        "Task ID": "id_str", # Will be processed further
        "Type": "type",
        "Name": "name",
        "Status": "status",
        "Project": "project_name_str", # For actions, tells which project it belongs to by name
        "Context": "context_str", # Legacy, might be useful for tag mapping if tags are missing
        "Start Date": "startDate_str",
        "Due Date": "dueDate_str",
        "Completion Date": "completionDate_str",
        "Duration": "duration_str",
        "Flagged": "flagged_str",
        "Notes": "notes",
        "Tags": "tags_str"
    }
    
    # Temporary storage for items to properly handle popping keys later
    processed_projects_temp: List[Dict[str, Any]] = []
    processed_actions_temp: List[Dict[str, Any]] = []

    try:
        with open(csv_file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row_dict in reader: # Changed variable name from 'row' to 'row_dict'
                item: Dict[str, Any] = {}
                # Store original row data for linking if needed, especially 'Project' name for actions
                # Correctly get the project name from the CSV "Project" column for the current action row
                original_project_name_for_action = row_dict.get("Project") 

                for csv_header, dict_key in header_map.items():
                    item[dict_key] = row_dict.get(csv_header)

                # Basic processing
                item_type = item.get("type")
                item_id_str = item.get("id_str")
                item_name = item.get("name", f"Unnamed Item {item_id_str}")
                item_status_csv = item.get("status", "").lower()
                
                # Skip if essential fields are missing
                if not item_type or not item_id_str:
                    print(f"Warning: Skipping row due to missing Type or Task ID: {row_dict}", file=sys.stderr)
                    continue

                # For consistency with JSON structure, and for querying
                item["id"] = item_id_str # Keep original CSV ID string for now
                item["name"] = item_name
                item["permalink"] = f"omnifocus:///task/{item_id_str}" # Placeholder, CSV IDs are not OF primary keys

                # Status mapping (simplified for CSV)
                # In CSV: Projects are 'active', 'inactive', 'done', 'dropped'. Actions often have blank status if active.
                if item_type == "Project":
                    if item_status_csv == "active": item["status"] = "Active"
                    elif item_status_csv == "done": item["status"] = "Completed" # Map "done" to "Completed"
                    elif item_status_csv == "dropped": item["status"] = "Dropped"
                    elif item_status_csv == "inactive": item["status"] = "OnHold" # Map "inactive" to "OnHold"
                    else: item["status"] = "Unknown"
                elif item_type == "Action":
                    if item.get("completionDate_str"): # If completion date is present, it's completed
                        item["status"] = "Completed"
                    elif item_status_csv == "dropped": # Explicitly dropped
                         item["status"] = "Dropped"
                    elif item_status_csv == "active" or item_status_csv == "": # Treat blank or "active" as available/active
                        item["status"] = "Active" # For CSV, map "active" or "" (if not completed) to "Active"
                    else: # other statuses like 'on hold' for an action
                        item["status"] = item_status_csv.capitalize() if item_status_csv else "Unknown"


                item["completed"] = bool(item.get("completionDate_str"))
                item["completionDate"] = parse_csv_date_to_iso(item.get("completionDate_str"))
                item["dueDate"] = parse_csv_date_to_iso(item.get("dueDate_str"))
                item["deferDate"] = parse_csv_date_to_iso(item.get("startDate_str")) # CSV 'Start Date' maps to Defer Date
                item["flagged"] = item.get("flagged_str", "").lower() == 'yes' # Assuming 'Yes' or empty

                # Tag processing
                tags_list = []
                tag_ids_list = [] # CSV doesn't have tag IDs, so we'll use names as IDs
                if item.get("tags_str"):
                    raw_tags = [t.strip() for t in item["tags_str"].split(',') if t.strip()]
                    for tag_name in raw_tags:
                        tags_list.append(tag_name)
                        tag_id_surrogate = f"tag_{tag_name.replace(' ', '_').lower()}" # Create a surrogate ID
                        tag_ids_list.append(tag_id_surrogate)
                        if tag_id_surrogate not in all_tags_found:
                            all_tags_found[tag_id_surrogate] = {"id": tag_id_surrogate, "name": tag_name}
                item["tags"] = tags_list
                item["tagIds"] = tag_ids_list
                
                # Store based on type
                if item_type == "Project":
                    processed_projects_temp.append(item) # Store processed item before popping
                elif item_type == "Action":
                    # Store the original project name with the action for later linking
                    item["_original_project_name_csv"] = original_project_name_for_action
                    processed_actions_temp.append(item) # Store processed item before popping
                
                # Clean up intermediate string fields from dict to avoid confusion
                # This step should ideally be done *after* the item is fully processed and linked,
                # or on copies. For now, we defer popping or do it on the final items.
                # We will handle this when constructing final_tasks_list and projects_dict

    except FileNotFoundError:
        print(f"Error: File not found at {csv_file_path}", file=sys.stderr)
        return {}
    except Exception as e:
        print(f"An unexpected error occurred during CSV parsing: {e}", file=sys.stderr)
        # import traceback
        # traceback.print_exc()
        return {}

    # --- Reconstruct Hierarchy for Tasks and Finalize Data Structures ---
    
    final_tasks_list: List[Dict[str, Any]] = []
    
    # Finalize projects_dict
    for proj_item_raw in processed_projects_temp:
        proj_item_final = proj_item_raw.copy()
        # Pop intermediate string fields for projects
        for key_to_remove in ["id_str", "status_str", "project_name_str", "context_str", 
                              "startDate_str", "dueDate_str", "completionDate_str", 
                              "duration_str", "flagged_str", "tags_str"]:
            proj_item_final.pop(key_to_remove, None)
        proj_item_final["tasks"] = [] # Initialize tasks list for project
        projects_dict[proj_item_final["id"]] = proj_item_final

    # Create a mapping from project name to project CSV ID for linking tasks
    project_name_to_id_map: Dict[str, str] = {
        proj_data["name"]: proj_id for proj_id, proj_data in projects_dict.items()
    }

    # Finalize tasks and attempt to link to projects
    for action_item_raw in processed_actions_temp:
        action_item_final = action_item_raw.copy()
        action_project_name_csv = action_item_final.pop("_original_project_name_csv", None)

        if action_project_name_csv and action_project_name_csv in project_name_to_id_map:
            parent_project_id = project_name_to_id_map[action_project_name_csv]
            action_item_final["projectId"] = parent_project_id
            # Optionally add to project's tasks list (if maintaining full hierarchy in projects_dict)
            if parent_project_id in projects_dict:
                # Ensure the tasks list exists
                if "tasks" not in projects_dict[parent_project_id]:
                    projects_dict[parent_project_id]["tasks"] = []
                projects_dict[parent_project_id]["tasks"].append(action_item_final) # Appending full task dictionary

        # Pop intermediate string fields for actions
        for key_to_remove in ["id_str", "status_str", "project_name_str", "context_str", 
                              "startDate_str", "dueDate_str", "completionDate_str", 
                              "duration_str", "flagged_str", "tags_str"]:
            action_item_final.pop(key_to_remove, None)
        
        # Basic parent ID from CSV Task ID
        task_id_parts = parse_csv_task_id(action_item_final["id"]) # id is original CSV Task ID string
        parent_id_str = get_parent_csv_task_id_str(task_id_parts)
        if parent_id_str:
            action_item_final["parentId"] = parent_id_str
        # The else block previously here was removed to clarify that parentId is for task-task relationships based on ID structure.
        # projectId handles the link to the parent project if applicable.

        # ---- START TEMP DEBUG ----
        # if action_item_final.get("id") == "90.1.1":
        #     print(f"DEBUG CSV Load - Task 90.1.1: original_project_name_csv='{action_project_name_csv}', computed_projectId='{action_item_final.get('projectId')}', computed_parentId='{action_item_final.get('parentId')}'", file=sys.stderr)
        # ---- END TEMP DEBUG ----

        final_tasks_list.append(action_item_final)

    # header_map_keys_by_value = {v: k for k, v in header_map.items()} # Removed as no longer used

    return {
        "all_tasks": final_tasks_list, 
        "projects_map": projects_dict,
        "folders_map": folders_dict, # Empty for CSV for now
        "tags_map": all_tags_found,
        "_csv_parser_warnings": "CSV Task parentId based on Task ID. Hierarchy within projects is basic."
    }
# --- END NEW CSV Parsing Functionality ---

@app.command("compare-sources")
def compare_sources_command(
    csv_file: str = typer.Option(
        ..., 
        "--csv-file", 
        help="Path to the OmniFocus CSV export file (comprehensive source).",
        exists=True, readable=True, file_okay=True, dir_okay=False
    ),
    json_file: str = typer.Option(
        ..., 
        "--json-file", 
        help="Path to the OmniFocus JSON export file (structured source for comparison).",
        exists=True, readable=True, file_okay=True, dir_okay=False
    ),
    # Add other options later, e.g., for output verbosity or specific fields to compare
):
    """
    Compares task data between a CSV export and a JSON export from OmniFocus.
    Identifies discrepancies in common fields like status, dates, tags, and project.
    """
    print(f"Loading data from CSV: {csv_file}", file=sys.stderr)
    csv_prepared_data = load_and_prepare_data_from_csv(csv_file)
    if not csv_prepared_data or not csv_prepared_data.get("all_tasks"):
        print("Error: No task data loaded from CSV or CSV task data is empty.", file=sys.stderr)
        raise typer.Exit(code=1)

    print(f"Loading data from JSON: {json_file}", file=sys.stderr)
    json_prepared_data = load_and_prepare_omnifocus_data(json_file)
    if not json_prepared_data or not json_prepared_data.get("all_tasks"):
        print("Warning: No task data loaded from JSON or JSON task data is empty. Comparison will be limited.", file=sys.stderr)
        # Allow to proceed if JSON is empty, as CSV is primary

    csv_tasks = csv_prepared_data.get("all_tasks", [])
    json_tasks = json_prepared_data.get("all_tasks", [])
    json_projects_map = json_prepared_data.get("projects_map", {})
    csv_projects_map = csv_prepared_data.get("projects_map", {})

    print(f"CSV tasks: {len(csv_tasks)}, JSON tasks: {len(json_tasks)}", file=sys.stderr)

    # Create a quick lookup for JSON tasks by name (case-insensitive)
    # This handles cases where multiple JSON tasks might have the same name; we'll pick the first for now.
    json_tasks_by_name_lower: Dict[str, Dict[str, Any]] = {}
    for task in json_tasks:
        name_lower = task.get("name", "").lower().strip()
        if name_lower and name_lower not in json_tasks_by_name_lower:
            json_tasks_by_name_lower[name_lower] = task

    discrepancies_found_count = 0
    csv_tasks_not_in_json_count = 0

    print("\n--- Task Discrepancy Report ---")

    for csv_task in csv_tasks:
        csv_task_name = csv_task.get("name", "").strip()
        csv_task_name_lower = csv_task_name.lower()
        csv_task_id = csv_task.get("id", "N/A")

        matched_json_task = json_tasks_by_name_lower.get(csv_task_name_lower)

        if not matched_json_task:
            # print(f"INFO: CSV Task '{csv_task_name}' (ID: {csv_task_id}) not found by name in JSON data.")
            csv_tasks_not_in_json_count += 1
            continue

        # --- Perform attribute comparison --- 
        task_discrepancies: List[str] = []

        # 1. Status
        csv_status = csv_task.get("status", "").lower()
        json_status = matched_json_task.get("status", "").lower()
        if csv_status != json_status:
            task_discrepancies.append(f"  - Status: CSV='{csv_task.get('status')}', JSON='{matched_json_task.get('status')}'")

        # 2. Due Date (using get_item_date for normalization)
        csv_due = get_item_date(csv_task.get("dueDate"))
        json_due = get_item_date(matched_json_task.get("dueDate"))
        if csv_due != json_due:
            task_discrepancies.append(f"  - DueDate: CSV='{csv_due}', JSON='{json_due}'")

        # 3. Defer Date
        csv_defer = get_item_date(csv_task.get("deferDate"))
        json_defer = get_item_date(matched_json_task.get("deferDate"))
        if csv_defer != json_defer:
            task_discrepancies.append(f"  - DeferDate: CSV='{csv_defer}', JSON='{json_defer}'")

        # 4. Completed Date
        csv_completed = get_item_date(csv_task.get("completionDate"))
        json_completed = get_item_date(matched_json_task.get("completedDate")) # JSON uses 'completedDate'
        if csv_completed != json_completed:
            task_discrepancies.append(f"  - CompletedDate: CSV='{csv_completed}', JSON='{json_completed}'")
        
        # 5. Tags (compare sorted list of tag names)
        csv_tags = sorted([t.lower() for t in csv_task.get("tags", [])])
        json_tag_ids = matched_json_task.get("tagIds", [])
        json_tags_map = json_prepared_data.get("tags_map", {})
        json_tag_names = sorted([json_tags_map.get(tag_id, {}).get("name", tag_id).lower() for tag_id in json_tag_ids])
        if csv_tags != json_tag_names:
            task_discrepancies.append(f"  - Tags: CSV='{csv_task.get('tags')}', JSON_Names='{[json_tags_map.get(tag_id, {}).get('name', tag_id) for tag_id in json_tag_ids]}'")

        # 6. Parent Project Name
        csv_project_id = csv_task.get("projectId")
        csv_project_name = csv_projects_map.get(csv_project_id, {}).get("name", "N/A") if csv_project_id else "N/A"
        
        json_project_id = matched_json_task.get("projectId")
        json_project_name = json_projects_map.get(json_project_id, {}).get("name", "N/A") if json_project_id else "N/A"

        if csv_project_name.lower().strip() != json_project_name.lower().strip():
            task_discrepancies.append(f"  - ProjectName: CSV='{csv_project_name}' (ID: {csv_project_id}), JSON='{json_project_name}' (ID: {json_project_id})")

        if task_discrepancies:
            print(f"Discrepancies for Task: '{csv_task_name}' (CSV ID: {csv_task_id}, JSON ID: {matched_json_task.get('id', 'N/A')})")
            for desc in task_discrepancies:
                print(desc)
            discrepancies_found_count += 1
            print("---") # Separator for tasks with discrepancies
    
    print("\n--- Comparison Summary ---")
    print(f"Total CSV tasks processed: {len(csv_tasks)}")
    print(f"Tasks found in CSV but not by name in JSON: {csv_tasks_not_in_json_count}")
    print(f"Tasks with matching names and detected discrepancies: {discrepancies_found_count}")

@app.command("generate-consolidated-tasks")
def generate_consolidated_tasks_command(
    csv_file: str = typer.Option(
        ...,
        "--csv-file",
        help="Path to the OmniFocus CSV export file (comprehensive source).",
        exists=True, readable=True, file_okay=True, dir_okay=False
    ),
    json_file: str = typer.Option(
        ...,
        "--json-file",
        help="Path to the OmniFocus JSON export file (for IDs and hierarchy).",
        exists=True, readable=True, file_okay=True, dir_okay=False
    ),
    output_file: Optional[str] = typer.Option(
        None, 
        "--output-file", "-o",
        help="Optional path to save the consolidated JSON output. Prints to stdout if not provided."
    ),
    fuzzy_match_threshold: int = typer.Option(
        90, # Default threshold
        "--fuzzy-threshold",
        help="Similarity threshold (0-100) for fuzzy name matching. Set to 0 to disable fuzzy matching if exact fails."
    ),
    output_unmatched_csv_file: Optional[str] = typer.Option(
        None,
        "--output-unmatched-csv-file",
        help="Optional path to save a JSON list of CSV tasks that were not matched in the JSON data."
    )
):
    """
    Generates a consolidated list of tasks, prioritizing CSV data and enriching it
    with IDs and hierarchy from the JSON export.
    """
    print(f"Loading CSV data from: {csv_file}...")
    csv_prepared_data = load_and_prepare_data_from_csv(csv_file)
    print(f"Loaded {len(csv_prepared_data.get('all_tasks', []))} tasks from CSV.")

    print(f"Loading JSON data from: {json_file}...")
    json_prepared_data = load_and_prepare_omnifocus_data(json_file)
    print(f"Loaded {len(json_prepared_data.get('all_tasks', []))} tasks from JSON.")

    # Prepare JSON tasks for quick lookup by normalized name
    json_tasks_by_name: Dict[str, List[Dict]] = {} # Store list to handle potential duplicate names
    for task in json_prepared_data.get('all_tasks', []):
        name = task.get('name', '')
        normalized_name = name.strip().lower()
        if normalized_name:
            if normalized_name not in json_tasks_by_name:
                json_tasks_by_name[normalized_name] = []
            json_tasks_by_name[normalized_name].append(task)

    # For fuzzy matching, we need a list of unique normalized JSON names
    unique_json_normalized_names = list(json_tasks_by_name.keys())

    consolidated_tasks_list = []
    json_matches_found = 0
    json_exact_matches = 0
    json_fuzzy_matches = 0
    unmatched_csv_tasks_list = [] # New list for unmatched CSV tasks

    csv_tasks_processed = 0
    for csv_task in csv_prepared_data.get('all_tasks', []):
        csv_tasks_processed +=1
        cons_task = {
            "csv_id": csv_task.get('id'),
            "csv_name": csv_task.get('name'),
            "csv_type": csv_task.get('type'),
            "csv_status": csv_task.get('status'),
            "csv_project_name": csv_task.get('_original_project_name_csv'),
            "csv_project_id_derived": csv_task.get('projectId'),
            "csv_due_date": csv_task.get('dueDate'),
            "csv_defer_date": csv_task.get('deferDate'),
            "csv_completion_date": csv_task.get('completionDate'),
            "csv_notes": csv_task.get('notes'),
            "csv_tags_str": csv_task.get("tags_str", ""),
            "csv_parsed_tags": sorted([t.strip().lower() for t in csv_task.get("tags_str", "").split(',') if t.strip()]),
            "csv_parent_id": csv_task.get('parentId'),
            "csv_flagged": csv_task.get('flagged'),
            "csv_estimated_minutes": csv_task.get('estimatedMinutes'),

            "json_data_found": False,
            "json_id": None,
            "json_name": None,
            "json_status": None,
            "json_project_id": None,
            "json_project_name": None,
            "json_folder_id": None,
            "json_folder_name": None,
            "json_due_date": None,
            "json_defer_date": None,
            "json_completion_date": None,
            "json_notes": None,
            "json_tags": [],
            "json_parent_id": None,
            "json_children_ids": [],
            "json_repetition_rule": None,
            "json_estimated_minutes": None,
            "json_flagged": None,
            "json_permalink": None,
            
            "_discrepancies": {},
            "_match_info": {}
        }

        # Attempt to find match(es) in JSON data
        csv_name_normalized = cons_task['csv_name'].strip().lower() if cons_task['csv_name'] else ""
        
        matched_json_tasks = []
        match_type = None
        match_score = None
        matched_json_name = None

        # 1. Try exact match
        if csv_name_normalized and csv_name_normalized in json_tasks_by_name:
            matched_json_tasks = json_tasks_by_name[csv_name_normalized]
            match_type = "exact"
            match_score = 100
            matched_json_name = csv_name_normalized
            json_exact_matches +=1
        
        # 2. If no exact match and fuzzy matching is enabled and we have names to search against
        elif fuzzy_match_threshold > 0 and csv_name_normalized and unique_json_normalized_names:
            # process.extractOne returns (choice, score)
            # We search for the csv_name_normalized within the list of unique_json_normalized_names
            fuzzy_result = process.extractOne(
                csv_name_normalized, 
                unique_json_normalized_names, 
                scorer=fuzz.WRatio, # WRatio is often good for comparing titles
                score_cutoff=fuzzy_match_threshold
            )
            if fuzzy_result:
                matched_json_name, match_score = fuzzy_result
                matched_json_tasks = json_tasks_by_name[matched_json_name] # Get the actual task(s)
                match_type = "fuzzy"
                json_fuzzy_matches += 1
        
        if matched_json_tasks:
            json_match = matched_json_tasks[0] # Take the first match
            if len(matched_json_tasks) > 1:
                # Log if multiple JSON tasks match this CSV task name (either exact or fuzzy)
                print(f"Warning: Multiple JSON tasks found for CSV task name '{cons_task['csv_name']}' (CSV ID: {cons_task['csv_id']}) via {match_type} match to JSON name '{matched_json_name}'. Using first match (JSON ID: {json_match.get('id')}).", file=sys.stderr)

            json_matches_found += 1 # Total matches (exact + fuzzy)
            cons_task['json_data_found'] = True
            cons_task['_match_info'] = {
                "type": match_type,
                "score": match_score,
                "csv_name_normalized": csv_name_normalized,
                "json_name_matched_normalized": matched_json_name
            }
            cons_task['json_id'] = json_match.get('id')
            cons_task['json_name'] = json_match.get('name')
            cons_task['json_status'] = json_match.get('status')
            cons_task['json_project_id'] = json_match.get('projectId')
            
            json_project_info = json_prepared_data.get('projects_map', {}).get(cons_task['json_project_id'], {}) if cons_task['json_project_id'] else {}
            cons_task['json_project_name'] = json_project_info.get('name')
            cons_task['json_folder_id'] = json_project_info.get('folderId')
            json_folder_info = json_prepared_data.get('folders_map', {}).get(cons_task['json_folder_id'], {}) if cons_task['json_folder_id'] else {}
            cons_task['json_folder_name'] = json_folder_info.get('name')
            
            cons_task['json_due_date'] = json_match.get('dueDate')
            cons_task['json_defer_date'] = json_match.get('deferDate')
            cons_task['json_completion_date'] = json_match.get('completionDate')
            cons_task['json_notes'] = json_match.get('note') # JSON uses 'note'
            
            json_tag_ids = json_match.get("tagIds", [])
            cons_task['json_tags'] = sorted([json_prepared_data.get("tags_map", {}).get(tag_id, {}).get("name", tag_id).lower() for tag_id in json_tag_ids])
            
            cons_task['json_parent_id'] = json_match.get('parentId')
            cons_task['json_children_ids'] = [child.get('id') for child in json_match.get('children', []) if child] # Ensure child is not None
            cons_task['json_repetition_rule'] = json_match.get('repetitionRule')
            cons_task['json_estimated_minutes'] = json_match.get('estimatedMinutes')
            cons_task['json_flagged'] = json_match.get('flagged')
            cons_task['json_permalink'] = json_match.get('permalink')

            # Populate _discrepancies
            if cons_task['csv_status'].lower() != str(cons_task['json_status']).lower(): # Ensure JSON status is string for comparison
                cons_task['_discrepancies']['status'] = {'csv': cons_task['csv_status'], 'json': cons_task['json_status']}
            
            # Project Name Discrepancy (comparing CSV's original project name with JSON's project name)
            csv_proj_name_norm = cons_task['csv_project_name'].strip().lower() if cons_task['csv_project_name'] else ""
            json_proj_name_norm = cons_task['json_project_name'].strip().lower() if cons_task['json_project_name'] else ""
            if csv_proj_name_norm != json_proj_name_norm:
                cons_task['_discrepancies']['project_name'] = {'csv': cons_task['csv_project_name'], 'json': cons_task['json_project_name'], 'csv_id': cons_task['csv_project_id_derived'], 'json_id': cons_task['json_project_id']}

            # Date Discrepancies (requires parsing to common format, e.g., date objects)
            csv_due_obj = get_item_date(cons_task['csv_due_date'])
            json_due_obj = get_item_date(cons_task['json_due_date'])
            if csv_due_obj != json_due_obj:
                 cons_task['_discrepancies']['due_date'] = {'csv': cons_task['csv_due_date'], 'json': cons_task['json_due_date']}

            csv_defer_obj = get_item_date(cons_task['csv_defer_date'])
            json_defer_obj = get_item_date(cons_task['json_defer_date'])
            if csv_defer_obj != json_defer_obj:
                 cons_task['_discrepancies']['defer_date'] = {'csv': cons_task['csv_defer_date'], 'json': cons_task['json_defer_date']}

            csv_compl_obj = get_item_date(cons_task['csv_completion_date'])
            json_compl_obj = get_item_date(cons_task['json_completion_date'])
            if csv_compl_obj != json_compl_obj:
                 cons_task['_discrepancies']['completion_date'] = {'csv': cons_task['csv_completion_date'], 'json': cons_task['json_completion_date']}

            # Notes Discrepancy
            if cons_task['csv_notes'] != cons_task['json_notes']: # Simple string comparison
                 cons_task['_discrepancies']['notes'] = {'csv_len': len(cons_task['csv_notes'] or ""), 'json_len': len(cons_task['json_notes'] or "")}


            # Tags Discrepancy
            if cons_task['csv_parsed_tags'] != cons_task['json_tags']:
                cons_task['_discrepancies']['tags'] = {'csv': cons_task['csv_parsed_tags'], 'json': cons_task['json_tags']}
            
            # Flagged Discrepancy
            # CSV stores "0" or "1", JSON stores boolean. Normalize CSV to boolean.
            csv_flagged_bool = cons_task['csv_flagged'] == "1" if cons_task['csv_flagged'] is not None else None
            # Ensure that json_flagged is not None before comparison if csv_flagged_bool is None, to avoid (None != False) being true
            if cons_task['json_flagged'] is None and csv_flagged_bool is None: # Both are None, no discrepancy
                 pass
            elif csv_flagged_bool != cons_task['json_flagged']:
                 cons_task['_discrepancies']['flagged'] = {'csv': cons_task['csv_flagged'], 'json': cons_task['json_flagged']}


        consolidated_tasks_list.append(cons_task)

    # Output results
    if output_file:
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(consolidated_tasks_list, f, indent=2)
            print(f"Consolidated data saved to: {output_file}")
        except IOError as e:
            print(f"Error writing to output file {output_file}: {e}", file=sys.stderr)
            print("Printing to stdout instead.")
            print(json.dumps(consolidated_tasks_list, indent=2))
    else:
        print(json.dumps(consolidated_tasks_list, indent=2))

    # Output unmatched CSV tasks if the option is provided
    if output_unmatched_csv_file:
        try:
            with open(output_unmatched_csv_file, 'w', encoding='utf-8') as f:
                json.dump(unmatched_csv_tasks_list, f, indent=2)
            print(f"Unmatched CSV tasks saved to: {output_unmatched_csv_file}")
        except IOError as e:
            print(f"Error writing unmatched CSV tasks to {output_unmatched_csv_file}: {e}", file=sys.stderr)

    print(f"--- Consolidation Summary ---")
    print(f"Total CSV tasks processed: {csv_tasks_processed}")
    print(f"Found JSON data for (total): {json_matches_found} tasks.")
    print(f"  - Exact name matches: {json_exact_matches}")
    print(f"  - Fuzzy name matches (threshold {fuzzy_match_threshold}%): {json_fuzzy_matches}")
    if csv_tasks_processed > 0:
        percentage_matched = (json_matches_found / csv_tasks_processed) * 100
        print(f"Percentage of CSV tasks matched in JSON: {percentage_matched:.2f}%")

@app.command("categorize-tasks")
def categorize_tasks_command(
    input_file: str = typer.Option(
        "data/consolidated_omnifocus_tasks.json", 
        "--input-file", "-i",
        help="Path to the consolidated OmniFocus tasks JSON file.",
        exists=True, readable=True, file_okay=True, dir_okay=False
    ),
    output_file: str = typer.Option(
        "data/categorized_tasks.json",
        "--output-file", "-o",
        help="Path to save the categorized tasks JSON output.",
        writable=True, file_okay=True, dir_okay=False # Writable checks if parent dir exists and is writable
    )
):
    """
    Categorizes tasks from the consolidated list into 'Actionable' or 'Reference'.
    'Reference' tasks are those with CSV status 'Completed' or 'Dropped'.
    All other tasks are 'Actionable' by default (further refinement may be needed).
    """
    print(f"--- Categorizing tasks from {input_file} ---")
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            consolidated_tasks = json.load(f)
    except FileNotFoundError:
        print(f"Error: Input file not found at {input_file}", file=sys.stderr)
        raise typer.Exit(code=1)
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {input_file}", file=sys.stderr)
        raise typer.Exit(code=1)

    # Accept both a list of tasks, a dict with 'tasks_map', or a dict with 'projects'
    if isinstance(consolidated_tasks, dict):
        if 'tasks_map' in consolidated_tasks:
            consolidated_tasks = list(consolidated_tasks['tasks_map'].values())
        elif 'projects' in consolidated_tasks:
            # Flatten all tasks from all projects
            projects = consolidated_tasks['projects']
            all_tasks = []
            for project in projects.values():
                all_tasks.extend(project.get('tasks', []))
            consolidated_tasks = all_tasks
        else:
            print(f"Error: Dict input does not contain 'tasks_map' or 'projects'. Keys: {list(consolidated_tasks.keys())}", file=sys.stderr)
            raise typer.Exit(code=1)
    elif not isinstance(consolidated_tasks, list):
        print(f"Error: Expected a list of tasks or a dict with 'tasks_map' or 'projects' in {input_file}, got {type(consolidated_tasks)}", file=sys.stderr)
        raise typer.Exit(code=1)

    categorized_tasks_list = []
    actionable_count = 0
    reference_count = 0
    flagged_actionable_count = 0

    for task in consolidated_tasks:
        if not isinstance(task, dict):
            print(f"Warning: Skipping non-dictionary item in consolidated tasks: {task}", file=sys.stderr)
            categorized_tasks_list.append(task) # Append as is if not a dict, or skip
            continue
        
        # Make a copy to avoid modifying the original task object in the list if it's reused
        task_copy = task.copy()
        # Use new export fields
        status = (task_copy.get("status") or "").capitalize()
        flagged = bool(task_copy.get("flagged", False))
        # Default category
        management_category = "Actionable"
        if status in ["Completed", "Dropped"]:
            management_category = "Reference"
        elif status not in ["Active", "Blocked", "Unknown"]:
            management_category = "Reference (Other Status)"
        task_copy["management_category"] = management_category
        if management_category == "Actionable":
            actionable_count += 1
            if flagged:
                flagged_actionable_count += 1
        else:
            reference_count += 1
        categorized_tasks_list.append(task_copy)

    print("\n--- Categorization Summary ---")
    print(f"Total tasks processed: {len(categorized_tasks_list)}")
    print(f"Tasks categorized as 'Actionable': {actionable_count}")
    print(f"  of which flagged: {flagged_actionable_count}")
    print(f"Tasks categorized as 'Reference': {reference_count}")

    try:
        output_dir = os.path.dirname(output_file)
        if output_dir: # Check if output_dir is not empty (i.e., not the current directory)
            os.makedirs(output_dir, exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(categorized_tasks_list, f, indent=2)
        print(f"Categorized tasks saved to {output_file}")
    except IOError as e:
        print(f"Error: Could not write categorized tasks to {output_file}: {e}", file=sys.stderr)
        raise typer.Exit(code=1)
    except Exception as e: # Catch other potential errors during makedirs or writing
        print(f"An unexpected error occurred during file writing or directory creation: {e}", file=sys.stderr)
        raise typer.Exit(code=1)

    # Print a sample of 'Actionable' and 'Reference' tasks for review
    print("\n--- Sample of 'Actionable' tasks for review ---")
    sample_count = 0
    max_sample_to_print = 10
    for task in categorized_tasks_list:
        if task.get("management_category") == "Actionable":
            if sample_count < max_sample_to_print:
                print(f"  Name: {task.get('name')}")
                print(f"    Status: {task.get('status')}")
                print(f"    Due: {task.get('dueDate')}")
                print(f"    Defer: {task.get('deferDate')}")
                print(f"    Flagged: {task.get('flagged')}")
                print(f"    Category: {task.get('management_category')}")
                print("    ----")
                sample_count += 1
            else:
                break
    if sample_count == 0:
        print("No tasks found in the 'Actionable' category to sample.")
    print("\n--- Sample of 'Reference' tasks for review ---")
    sample_count = 0
    for task in categorized_tasks_list:
        if task.get("management_category").startswith("Reference"):
            if sample_count < max_sample_to_print:
                print(f"  Name: {task.get('name')}")
                print(f"    Status: {task.get('status')}")
                print(f"    Due: {task.get('dueDate')}")
                print(f"    Defer: {task.get('deferDate')}")
                print(f"    Flagged: {task.get('flagged')}")
                print(f"    Category: {task.get('management_category')}")
                print("    ----")
                sample_count += 1
            else:
                break
    if sample_count == 0:
        print("No tasks found in the 'Reference' category to sample.")

@app.command("summary")
def summary_command(
    json_file: str = typer.Option(
        get_latest_json_export_path(),
        "--file",
        help="Path to the OmniFocus JSON export file. Defaults to latest export.",
    )
):
    """
    Print a summary of the number of tasks, projects, folders, and tags in the given OmniFocus JSON export.
    """
    data = load_and_prepare_omnifocus_data(json_file)
    if not data:
        print(f"Error: Could not load or parse data from {json_file}", file=sys.stderr)
        raise typer.Exit(code=1)
    print(f"Summary for {json_file}:")
    print(f"  Tasks:   {len(data['all_tasks'])}")
    print(f"  Projects: {len(data['projects_map'])}")
    print(f"  Folders:  {len(data['folders_map'])}")
    print(f"  Tags:     {len(data['tags_map'])}")

def pretty_print_item(item: dict, prepared_data: dict) -> None:
    """Pretty-print a single task, project, or folder in a human-readable format."""
    item_type = item.get("type", "Task").capitalize()
    print(f"{'='*60}")
    print(f"{item_type} Details")
    print(f"{'='*60}")
    print(f"Name:      {item.get('name', 'Unnamed')}")
    print(f"ID:        {item.get('id', 'N/A')}")
    if item.get("status"):
        print(f"Status:    {item.get('status')}")
    if item.get("completed") is not None:
        print(f"Completed: {item.get('completed')}")
    if item.get("dueDate"):
        print(f"Due:       {item.get('dueDate')}")
    if item.get("deferDate"):
        print(f"Defer:     {item.get('deferDate')}")
    if item.get("completedDate"):
        print(f"Completed: {item.get('completedDate')}")
    if item.get("flagged") is not None:
        print(f"Flagged:   {item.get('flagged')}")
    if item.get("estimatedMinutes"):
        print(f"Est. Min.: {item.get('estimatedMinutes')}")
    if item.get("projectId"):
        project_id_val = item['projectId']
        project_info = prepared_data.get("projects_map", {}).get(project_id_val, {})
        project_name = project_info.get("name", "Unknown Project")
        print(f"Project:   {project_name} (ID: {project_id_val})")
        folder_id_val = project_info.get("folderId")
        if folder_id_val:
            folder_info = prepared_data.get("folders_map", {}).get(folder_id_val, {})
            folder_name = folder_info.get("name", "Unknown Folder")
            print(f"  Folder:  {folder_name} (ID: {folder_id_val})")
    if item.get("parentId"):
        print(f"Parent:    {item.get('parentId')}")
    if item.get("tagIds"):
        print(f"Tags:      {', '.join(item.get('tagIds', []))}")
    if item.get("permalink"):
        print(f"Permalink: {item.get('permalink')}")
    # Print notes, parsing embedded \n as real newlines
    notes = item.get("notes") or item.get("note")
    if notes:
        print(f"{'-'*60}\nNotes:")
        print(notes.replace('\\n', '\n'))
    print(f"{'='*60}")

def get_tasks_for_project(project_id: str, prepared_data: dict) -> list:
    """Return all tasks belonging to a project, top-level only (not subtasks)."""
    return [t for t in prepared_data.get("all_tasks", []) if t.get("projectId") == project_id and not t.get("parentId")]

@app.command("next")
def next_command():
    """
    Shows a focused list of next actions to reduce overwhelm.
    """
    handle_next(None) # No arguments are passed for now

@app.command("archive-completed")
def archive_completed_command(
    file: Optional[str] = typer.Option(get_latest_json_export_path(), "--file", "-f", help="Path to the OmniFocus JSON export file (defaults to latest export)."),
    age_days: int = typer.Option(0, "--age-days", "-a", help="Minimum age in days for archiving completed items (0 = archive all completed items immediately)."),
    dry_run: bool = typer.Option(False, "--dry-run", "-n", help="Show what would be archived without making changes."),
    force: bool = typer.Option(False, "--force", help="Archive without confirmation prompt."),
    delete_from_omnifocus: bool = typer.Option(False, "--delete-from-omnifocus", "-d", help="Also delete archived items from the live OmniFocus database (RECOMMENDED for true archival).")
):
    """Archive completed/old OmniFocus content to reference_archive/ directory."""
    args = type('Args', (), {
        'file': file,
        'age_days': age_days,
        'dry_run': dry_run,
        'force': force,
        'delete_from_omnifocus': delete_from_omnifocus
    })
    handle_archive_completed(args)

@app.command("diagnostics")
def diagnostics():
    """Comprehensive health check – export, validation, DB ingest, duplicates."""
    from .utils.logger import get_logger
    log = get_logger("diagnostics")

    console = Console()

    # 1) OmniFocus app process
    try:
        result = subprocess.run(["pgrep", "-x", "OmniFocus"], capture_output=True)
        is_running = result.returncode == 0
    except Exception as e:
        is_running = False
        error_msg = str(e)
    console.print(("✅" if is_running else "❌") + " OmniFocus running", style="green" if is_running else "red")
    if not is_running and 'error_msg' in locals():
        console.print(f"    {error_msg}")

    # 2) Latest export & validation
    try:
        from .utils.ensure_export import ensure_fresh_export
        export_path = ensure_fresh_export(1800)
        console.print(f"✅ Latest export: {export_path}", style="green")
    except Exception as e:
        console.print(f"❌ Export failed: {e}", style="red")
        export_path = None

    # 3) Counts & validation via loader
    if export_path:
        from .utils.data_loading import load_and_prepare_omnifocus_data
        data = load_and_prepare_omnifocus_data(export_path)
        if data:
            console.print(
                f"✅ Export validation passed – Tasks: {len(data['all_tasks'])}, Projects: {len(data['projects_map'])}",
                style="green",
            )
        else:
            console.print("❌ Export validation failed – see above errors", style="red")

    # 4) DB status
    db_path = Path("data/omnifocus.sqlite")
    if db_path.exists():
        import sqlite3, datetime as _dt
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("SELECT MAX(lastSeen) FROM tasks")
        last_seen = cur.fetchone()[0]
        conn.close()
        console.print(f"✅ DB present – lastSeen max: {last_seen}", style="green")
    else:
        console.print("❌ SQLite DB not found. Run 'ofcli ingest' first.", style="red")

    # 5) Potential duplicates from last ingest report
    # (simple heuristic: flag tasks with same name+project appearing >1)
    if db_path.exists():
        import sqlite3
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute(
            "SELECT name, projectId, COUNT(*) FROM tasks GROUP BY name, projectId HAVING COUNT(*) > 1 LIMIT 5"
        )
        dups = cur.fetchall()
        conn.close()
        if dups:
            console.print(f"⚠️  Potential duplicate tasks found ({len(dups)} samples):", style="yellow")
            for name, pid, cnt in dups:
                console.print(f"   • '{name}' (project {pid or 'None'}) – {cnt} copies")
        else:
            console.print("✅ No duplicate tasks detected (name+project heuristic)", style="green")

@app.command("ingest")
def ingest_command(
    age: int = typer.Option(1800, "--age", "-a", help="Max age (seconds) before triggering a new export."),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Suppress subprocess output"),
):
    """Ensure fresh export, archive it, and update the SQLite DB."""
    script_path = Path(__file__).resolve().parent.parent / "tools" / "scripts" / "ingest_export.py"
    cmd = ["python3", str(script_path), "--age", str(age)]
    if quiet:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(result.stderr, file=sys.stderr)
            raise typer.Exit(code=1)
    else:
        subprocess.run(cmd, check=True)
    if not quiet:
        print("Ingestion complete.")

# =======================
# Next Actions Command
# =======================

@app.command("next-actions")
def next_actions_command(
    limit: int = typer.Option(50, "--limit", "-l", help="Maximum number of tasks to show."),
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Filter to a specific project name or ID."),
    flagged_only: bool = typer.Option(False, "--flagged-only", "-f", help="Show only flagged next actions."),
):
    """Show a focused list of Available / Next tasks from the SQLite database."""

    # Ensure DB is up to date
    script_path = Path(__file__).resolve().parent.parent / "tools" / "scripts" / "ingest_export.py"
    subprocess.run(["python3", str(script_path), "--age", "900"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    db_path = Path("data/omnifocus.sqlite")
    if not db_path.exists():
        print("Database not found. Run 'ofcli ingest' first.", file=sys.stderr)
        raise typer.Exit(code=1)

    import sqlite3, datetime as _dt

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    status_set = ("Available", "Next")
    sql = "SELECT t.id, t.name, t.dueDate, t.flagged, p.name AS projectName FROM tasks t " \
          "LEFT JOIN projects p ON p.id = t.projectId " \
          "WHERE t.status IN (?, ?)"
    params = list(status_set)

    if flagged_only:
        sql += " AND t.flagged = 1"

    if project:
        # Accept either project ID or name (case-insensitive)
        sql += " AND (p.id = ? OR lower(p.name) = lower(?))"
        params.extend([project, project])

    sql += " ORDER BY t.flagged DESC, t.dueDate IS NULL, t.dueDate ASC LIMIT ?"
    params.append(limit)

    cur.execute(sql, params)
    rows = cur.fetchall()

    if not rows:
        print("No next actions found with given filters.")
        return

    print(f"Next Actions (showing {len(rows)}/{limit}):")
    for r in rows:
        due_disp = r["dueDate"][:10] if r["dueDate"] else ""
        flag_icon = "★ " if r["flagged"] else "  "
        proj = r["projectName"] or "(No Project)"
        print(f"{flag_icon}{r['name']}  [Project: {proj}]{'  Due:' + due_disp if due_disp else ''}")
    conn.close()

# =====================
# Dashboard Command
# =====================

@app.command("dashboard")
def dashboard_command(
    open_browser: bool = typer.Option(False, "--open", "-o", help="Open HTML dashboard in browser."),
):
    """Generate today's Markdown + HTML dashboard report."""
    script_path = Path(__file__).resolve().parent.parent / "tools" / "scripts" / "generate_dashboard.py"
    cmd = ["python3", str(script_path)]
    if open_browser:
        cmd.append("--open")
    subprocess.run(cmd, check=True)
    print("Dashboard generated.")

# ---------------------------------------------------------------------------
# Diagnostics: Task/Project tree statistics
# ---------------------------------------------------------------------------


@app.command("schedule")
def schedule_command(
    title: str = typer.Option(..., "--title", "-t", help="Title of the event."),
    description: str = typer.Option(..., "--description", "-d", help="Description of the event."),
    date: str = typer.Option(..., "--date", help="Event date (YYYY-MM-DD)."),
    time: str = typer.Option("08:00", "--time", help="Event start time (HH:MM, 24-hour, default: 08:00)."),
    location: str = typer.Option(..., "--location", "-l", help="Event location."),
    attendees: str = typer.Option(..., "--attendees", help="Comma-separated list of attendees (family members)."),
    duration: int = typer.Option(60, "--duration", help="Duration in minutes (default: 60)."),
    priority: str = typer.Option("medium", "--priority", help="Event priority (low, medium, high, critical)."),
    create_event: bool = typer.Option(True, "--create-event", help="Automatically create calendar event."),
    task_id: Optional[str] = typer.Option(None, "--task-id", help="Specific OmniFocus Task ID to complete after scheduling (for precise matching)."),
):
    """Schedule a family event with calendar integration and conflict analysis."""
    try:
        from .commands.schedule_family import schedule_family_event
        attendee_list = [a.strip() for a in attendees.split(",")]
        analysis = schedule_family_event(
            title=title,
            description=description,
            date_str=date,
            location_name=location,
            attendees=attendee_list,
            duration_minutes=duration,
            priority=priority,
            create_calendar_event=create_event,
            time_str=time,
            task_id=task_id
        )
        print("✅ Family scheduling completed successfully!")
    except ImportError as e:
        print(f"❌ Error importing family scheduler: {e}")
    except Exception as e:
        print(f"❌ Error in family scheduling: {e}")

@app.command("tree-stats")
def tree_stats_command(
    file: str = typer.Option(get_latest_json_export_path(), "--file", help="Path to the OmniFocus JSON export file."),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON instead of text."),
    top: int = typer.Option(20, "--top", help="Show N largest projects/folders."),
    state_breakdown: bool = typer.Option(False, "--state-breakdown", help="Include per-depth state counts."),
    soon: int = typer.Option(7, "--soon", help="Days window for 'due soon' stats."),
):
    """Print statistics about task counts and nesting depth across the database."""

    print(f"Loading export from: {file}")
    prepared = load_and_prepare_omnifocus_data(file)
    tasks = prepared.get("all_tasks", [])
    projects_map = prepared.get("projects_map", {})
    folders_map = prepared.get("folders_map", {})

    # Build lookup for parent relationships
    id_to_task = {t["id"]: t for t in tasks}

    def depth(task):
        d = 1
        current = task
        # Walk parent chain inside tasks only
        while current.get("parentId"):
            parent = id_to_task.get(current["parentId"])
            if not parent:
                break
            d += 1
            current = parent
        return d

    depth_histogram: dict[int, int] = {}
    project_counts: dict[str, int] = {}
    depth_state: dict[int, dict[str, int]] = {}

    for t in tasks:
        d = depth(t)
        depth_histogram[d] = depth_histogram.get(d, 0) + 1

        proj_id = t.get("projectId")
        if proj_id:
            project_counts[proj_id] = project_counts.get(proj_id, 0) + 1

        # state tallies
        state_bucket = depth_state.setdefault(d, {"active": 0, "completed": 0, "due": 0, "defer": 0})
        if t.get("completed") or t.get("status") == "Completed":
            state_bucket["completed"] += 1
        else:
            state_bucket["active"] += 1
        if t.get("dueDate"):
            state_bucket["due"] += 1
        if t.get("deferDate"):
            state_bucket["defer"] += 1

    max_depth = max(depth_histogram) if depth_histogram else 0

    # Build project display list
    top_projects = sorted(project_counts.items(), key=lambda kv: kv[1], reverse=True)[: top]

    today = datetime.utcnow().date()
    soon_limit = today + timedelta(days=soon)

    overdue = 0
    due_soon = 0
    active_tasks = 0
    completed_tasks = 0
    flagged_tasks = 0
    with_due = 0
    with_defer = 0

    for t in tasks:
        is_completed = t.get("completed") or t.get("status") == "Completed"
        if is_completed:
            completed_tasks += 1
        else:
            active_tasks += 1
        if t.get("flagged"):
            flagged_tasks += 1
        due_str = t.get("dueDate")
        if due_str:
            with_due += 1
            try:
                due_date = datetime.fromisoformat(due_str.rstrip("Z")).date()
                if not is_completed and due_date < today:
                    overdue += 1
                elif not is_completed and today <= due_date <= soon_limit:
                    due_soon += 1
            except Exception:
                pass
        if t.get("deferDate"):
            with_defer += 1

    without_dates = len(tasks) - with_due - with_defer

    stats = {
        "total_tasks": len(tasks),
        "active_tasks": active_tasks,
        "completed_tasks": completed_tasks,
        "flagged_tasks": flagged_tasks,
        "with_due": with_due,
        "with_defer": with_defer,
        "without_dates": without_dates,
        "overdue": overdue,
        "due_soon": due_soon,
        "soon_window_days": soon,
        "max_depth": max_depth,
        "depth_histogram": depth_histogram,
        "depth_state": depth_state if state_breakdown else None,
        "top_projects": [
            {
                "project_id": pid,
                "name": projects_map.get(pid, {}).get("name", "Unknown"),
                "task_count": cnt,
                "folder": folders_map.get(projects_map.get(pid, {}).get("folderId", ""), {}).get("name", "") or None,
            }
            for pid, cnt in top_projects
        ],
    }

    if json_output:
        import json

        print(json.dumps(stats, indent=2))
    else:
        print("\n=== OmniFocus Tree Statistics ===")
        print(f"Active: {stats['active_tasks']}  |  Completed: {stats['completed_tasks']}  |  Flagged: {stats['flagged_tasks']}")
        print(f"With due: {stats['with_due']}  |  With defer: {stats['with_defer']}  |  No dates: {stats['without_dates']}")
        print(f"Overdue: {stats['overdue']}  |  Due in next {soon} days: {stats['due_soon']}")
        print(f"Total tasks: {stats['total_tasks']}")
        print(f"Maximum depth: {stats['max_depth']}\n")

        print("Depth histogram:")
        for level in sorted(stats["depth_histogram"].keys()):
            print(f"  Level {level}: {stats['depth_histogram'][level]}")

        print(f"\nTop {top} projects by task count:")
        for p in stats["top_projects"]:
            line = f"  • {p['name']} (ID {p['project_id']}) – {p['task_count']} tasks"
            if p.get("folder"):
                line += f" [Folder: {p['folder']}]"
            print(line)

        if state_breakdown:
            print("\nPer-depth state breakdown:")
            for level in sorted(depth_state.keys()):
                s = depth_state[level]
                print(
                    f"  Level {level}: active {s['active']}, completed {s['completed']}, due {s['due']}, defer {s['defer']}"
                )

@app.command("emergency-calendar")
def emergency_calendar():
    """Emergency calendar access when automated methods fail (opens Calendar.app)."""
    from .commands.emergency_calendar_command import handle_emergency_calendar
    args = type('Args', (), {})
    handle_emergency_calendar(args)

@app.command("emergency-calendar-analysis")  
def emergency_calendar_analysis():
    """Analyze why automated calendar methods are failing."""
    from .commands.emergency_calendar_command import handle_emergency_calendar_report
    args = type('Args', (), {})
    handle_emergency_calendar_report(args)

@app.command("calendar-today")
def calendar_today():
    """Show today's calendar events using EventKit (FAST - no timeouts)."""
    from .commands.eventkit_calendar_command import handle_eventkit_calendar_today
    args = type('Args', (), {})
    handle_eventkit_calendar_today(args)

@app.command("calendar-family") 
def calendar_family():
    """Show family calendar events using EventKit (FAST - no timeouts)."""
    from .commands.eventkit_calendar_command import handle_eventkit_family_events
    args = type('Args', (), {})
    handle_eventkit_family_events(args)

@app.command("calendar-conflicts")
def calendar_conflicts(
    start_time: str = typer.Option(..., "--start", "-s", help="Start time (YYYY-MM-DD HH:MM)"),
    end_time: str = typer.Option(..., "--end", "-e", help="End time (YYYY-MM-DD HH:MM)"),
):
    """Check for calendar conflicts using EventKit (FAST - no timeouts)."""
    from .commands.eventkit_calendar_command import handle_eventkit_calendar_conflicts
    args = type('Args', (), {
        'start_time': start_time,
        'end_time': end_time
    })
    handle_eventkit_calendar_conflicts(args)

# === Bulk Operations ===

@app.command("bulk-complete")
def bulk_complete_command(
    task_ids: List[str] = typer.Argument(..., help="List of task IDs to complete."),
    dry_run: bool = typer.Option(False, "--dry-run", "-n", help="Show what would be completed without making changes."),
    force: bool = typer.Option(False, "--force", help="Complete without confirmation prompt."),
):
    """Complete multiple tasks in bulk."""
    if not task_ids:
        print("No task IDs provided.", file=sys.stderr)
        raise typer.Exit(code=1)
    
    if not force and not dry_run:
        print(f"About to complete {len(task_ids)} tasks:")
        for task_id in task_ids:
            print(f"  - {task_id}")
        if not typer.confirm("Continue?"):
            raise typer.Exit()
    
    from omnifocus_api.apple_script_client import complete_task
    
    success_count = 0
    failed_tasks = []
    
    for task_id in task_ids:
        try:
            if not dry_run:
                if complete_task(task_id):
                    success_count += 1
                    print(f"✅ Completed task: {task_id}")
                else:
                    failed_tasks.append(task_id)
                    print(f"❌ Failed to complete task: {task_id}")
            else:
                print(f"📋 Would complete task: {task_id}")
                success_count += 1
        except Exception as e:
            failed_tasks.append(task_id)
            print(f"❌ Error completing task {task_id}: {e}")
    
    print(f"\nSummary: {success_count} tasks {'completed' if not dry_run else 'would be completed'}")
    if failed_tasks:
        print(f"Failed tasks: {', '.join(failed_tasks)}")

@app.command("bulk-flag")
def bulk_flag_command(
    task_ids: List[str] = typer.Argument(..., help="List of task IDs to flag."),
    dry_run: bool = typer.Option(False, "--dry-run", "-n", help="Show what would be flagged without making changes."),
    force: bool = typer.Option(False, "--force", help="Flag without confirmation prompt."),
):
    """Flag multiple tasks in bulk."""
    if not task_ids:
        print("No task IDs provided.", file=sys.stderr)
        raise typer.Exit(code=1)
    
    if not force and not dry_run:
        print(f"About to flag {len(task_ids)} tasks:")
        for task_id in task_ids:
            print(f"  - {task_id}")
        if not typer.confirm("Continue?"):
            raise typer.Exit()
    
    from omnifocus_api.apple_script_client import execute_omnifocus_applescript
    
    success_count = 0
    failed_tasks = []
    
    for task_id in task_ids:
        try:
            if not dry_run:
                script = f'''
tell application "OmniFocus"
    tell default document
        set targetTask to first flattened task whose id is "{task_id}"
        set flagged of targetTask to true
    end tell
end tell
'''
                execute_omnifocus_applescript(script)
                success_count += 1
                print(f"✅ Flagged task: {task_id}")
            else:
                print(f"📋 Would flag task: {task_id}")
                success_count += 1
        except Exception as e:
            failed_tasks.append(task_id)
            print(f"❌ Error flagging task {task_id}: {e}")
    
    print(f"\nSummary: {success_count} tasks {'flagged' if not dry_run else 'would be flagged'}")
    if failed_tasks:
        print(f"Failed tasks: {', '.join(failed_tasks)}")

@app.command("bulk-unflag")
def bulk_unflag_command(
    task_ids: List[str] = typer.Argument(..., help="List of task IDs to unflag."),
    dry_run: bool = typer.Option(False, "--dry-run", "-n", help="Show what would be unflagged without making changes."),
    force: bool = typer.Option(False, "--force", help="Unflag without confirmation prompt."),
):
    """Unflag multiple tasks in bulk."""
    if not task_ids:
        print("No task IDs provided.", file=sys.stderr)
        raise typer.Exit(code=1)
    
    if not force and not dry_run:
        print(f"About to unflag {len(task_ids)} tasks:")
        for task_id in task_ids:
            print(f"  - {task_id}")
        if not typer.confirm("Continue?"):
            raise typer.Exit()
    
    from omnifocus_api.apple_script_client import unflag_task
    
    success_count = 0
    failed_tasks = []
    
    for task_id in task_ids:
        try:
            if not dry_run:
                if unflag_task(task_id):
                    success_count += 1
                    print(f"✅ Unflagged task: {task_id}")
                else:
                    failed_tasks.append(task_id)
                    print(f"❌ Failed to unflag task: {task_id}")
            else:
                print(f"📋 Would unflag task: {task_id}")
                success_count += 1
        except Exception as e:
            failed_tasks.append(task_id)
            print(f"❌ Error unflagging task {task_id}: {e}")
    
    print(f"\nSummary: {success_count} tasks {'unflagged' if not dry_run else 'would be unflagged'}")
    if failed_tasks:
        print(f"Failed tasks: {', '.join(failed_tasks)}")

@app.command("bulk-move")
def bulk_move_command(
    task_ids: List[str] = typer.Argument(..., help="List of task IDs to move."),
    project_name: str = typer.Option(..., "--project", "-p", help="Name of the project to move tasks to."),
    dry_run: bool = typer.Option(False, "--dry-run", "-n", help="Show what would be moved without making changes."),
    force: bool = typer.Option(False, "--force", help="Move without confirmation prompt."),
):
    """Move multiple tasks to a project in bulk."""
    if not task_ids:
        print("No task IDs provided.", file=sys.stderr)
        raise typer.Exit(code=1)
    
    if not force and not dry_run:
        print(f"About to move {len(task_ids)} tasks to project '{project_name}':")
        for task_id in task_ids:
            print(f"  - {task_id}")
        if not typer.confirm("Continue?"):
            raise typer.Exit()
    
    from omnifocus_api.apple_script_client import move_task_to_project
    
    success_count = 0
    failed_tasks = []
    
    for task_id in task_ids:
        try:
            if not dry_run:
                if move_task_to_project(task_id, project_name):
                    success_count += 1
                    print(f"✅ Moved task {task_id} to project '{project_name}'")
                else:
                    failed_tasks.append(task_id)
                    print(f"❌ Failed to move task {task_id} to project '{project_name}'")
            else:
                print(f"📋 Would move task {task_id} to project '{project_name}'")
                success_count += 1
        except Exception as e:
            failed_tasks.append(task_id)
            print(f"❌ Error moving task {task_id}: {e}")
    
    print(f"\nSummary: {success_count} tasks {'moved' if not dry_run else 'would be moved'} to project '{project_name}'")
    if failed_tasks:
        print(f"Failed tasks: {', '.join(failed_tasks)}")

@app.command("bulk-set-due")
def bulk_set_due_command(
    task_ids: List[str] = typer.Argument(..., help="List of task IDs to set due date for."),
    due_date: str = typer.Option(..., "--due", "-d", help="Due date (YYYY-MM-DD or natural language)."),
    dry_run: bool = typer.Option(False, "--dry-run", "-n", help="Show what would be updated without making changes."),
    force: bool = typer.Option(False, "--force", help="Update without confirmation prompt."),
):
    """Set due date for multiple tasks in bulk."""
    if not task_ids:
        print("No task IDs provided.", file=sys.stderr)
        raise typer.Exit(code=1)
    
    if not force and not dry_run:
        print(f"About to set due date '{due_date}' for {len(task_ids)} tasks:")
        for task_id in task_ids:
            print(f"  - {task_id}")
        if not typer.confirm("Continue?"):
            raise typer.Exit()
    
    from omnifocus_api.apple_script_client import set_task_due_date
    
    success_count = 0
    failed_tasks = []
    
    for task_id in task_ids:
        try:
            if not dry_run:
                if set_task_due_date(task_id, due_date):
                    success_count += 1
                    print(f"✅ Set due date '{due_date}' for task: {task_id}")
                else:
                    failed_tasks.append(task_id)
                    print(f"❌ Failed to set due date for task: {task_id}")
            else:
                print(f"📋 Would set due date '{due_date}' for task: {task_id}")
                success_count += 1
        except Exception as e:
            failed_tasks.append(task_id)
            print(f"❌ Error setting due date for task {task_id}: {e}")
    
    print(f"\nSummary: {success_count} tasks {'updated' if not dry_run else 'would be updated'} with due date '{due_date}'")
    if failed_tasks:
        print(f"Failed tasks: {', '.join(failed_tasks)}")

@app.command("bulk-set-defer")
def bulk_set_defer_command(
    task_ids: List[str] = typer.Argument(..., help="List of task IDs to set defer date for."),
    defer_date: str = typer.Option(..., "--defer", "-d", help="Defer date (YYYY-MM-DD or natural language)."),
    dry_run: bool = typer.Option(False, "--dry-run", "-n", help="Show what would be updated without making changes."),
    force: bool = typer.Option(False, "--force", help="Update without confirmation prompt."),
):
    """Set defer date for multiple tasks in bulk."""
    if not task_ids:
        print("No task IDs provided.", file=sys.stderr)
        raise typer.Exit(code=1)
    
    if not force and not dry_run:
        print(f"About to set defer date '{defer_date}' for {len(task_ids)} tasks:")
        for task_id in task_ids:
            print(f"  - {task_id}")
        if not typer.confirm("Continue?"):
            raise typer.Exit()
    
    from omnifocus_api.apple_script_client import set_task_defer_date
    
    success_count = 0
    failed_tasks = []
    
    for task_id in task_ids:
        try:
            if not dry_run:
                if set_task_defer_date(task_id, defer_date):
                    success_count += 1
                    print(f"✅ Set defer date '{defer_date}' for task: {task_id}")
                else:
                    failed_tasks.append(task_id)
                    print(f"❌ Failed to set defer date for task: {task_id}")
            else:
                print(f"📋 Would set defer date '{defer_date}' for task: {task_id}")
                success_count += 1
        except Exception as e:
            failed_tasks.append(task_id)
            print(f"❌ Error setting defer date for task {task_id}: {e}")
    
    print(f"\nSummary: {success_count} tasks {'updated' if not dry_run else 'would be updated'} with defer date '{defer_date}'")
    if failed_tasks:
        print(f"Failed tasks: {', '.join(failed_tasks)}")

@app.command("bulk-project-status")
def bulk_project_status_command(
    project_ids: List[str] = typer.Argument(..., help="List of project IDs to change status for."),
    status: str = typer.Option(..., "--status", "-s", help="New status (Active, OnHold, Dropped, Done)."),
    dry_run: bool = typer.Option(False, "--dry-run", "-n", help="Show what would be updated without making changes."),
    force: bool = typer.Option(False, "--force", help="Update without confirmation prompt."),
):
    """Change status for multiple projects in bulk."""
    if not project_ids:
        print("No project IDs provided.", file=sys.stderr)
        raise typer.Exit(code=1)
    
    valid_statuses = ["Active", "OnHold", "Dropped", "Done"]
    if status not in valid_statuses:
        print(f"Invalid status '{status}'. Valid statuses: {', '.join(valid_statuses)}", file=sys.stderr)
        raise typer.Exit(code=1)
    
    if not force and not dry_run:
        print(f"About to set status '{status}' for {len(project_ids)} projects:")
        for project_id in project_ids:
            print(f"  - {project_id}")
        if not typer.confirm("Continue?"):
            raise typer.Exit()
    
    from omnifocus_api.apple_script_client import execute_omnifocus_applescript
    
    success_count = 0
    failed_projects = []
    
    for project_id in project_ids:
        try:
            if not dry_run:
                script = f'''
tell application "OmniFocus"
    tell default document
        set targetProject to first flattened project whose id is "{project_id}"
        set status of targetProject to status "{status}"
    end tell
end tell
'''
                execute_omnifocus_applescript(script)
                success_count += 1
                print(f"✅ Set status '{status}' for project: {project_id}")
            else:
                print(f"📋 Would set status '{status}' for project: {project_id}")
                success_count += 1
        except Exception as e:
            failed_projects.append(project_id)
            print(f"❌ Error setting status for project {project_id}: {e}")
    
    print(f"\nSummary: {success_count} projects {'updated' if not dry_run else 'would be updated'} with status '{status}'")
    if failed_projects:
        print(f"Failed projects: {', '.join(failed_projects)}")

@app.command("bulk-delete")
def bulk_delete_command(
    item_ids: List[str] = typer.Argument(..., help="List of task or project IDs to delete."),
    item_type: str = typer.Option("tasks", "--type", "-t", help="Type of items to delete (tasks or projects)."),
    dry_run: bool = typer.Option(False, "--dry-run", "-n", help="Show what would be deleted without making changes."),
    force: bool = typer.Option(False, "--force", help="Delete without confirmation prompt."),
):
    """Delete multiple tasks or projects in bulk."""
    if not item_ids:
        print("No item IDs provided.", file=sys.stderr)
        raise typer.Exit(code=1)
    
    if item_type not in ["tasks", "projects"]:
        print("Invalid item type. Must be 'tasks' or 'projects'.", file=sys.stderr)
        raise typer.Exit(code=1)
    
    if not force and not dry_run:
        print(f"About to delete {len(item_ids)} {item_type}:")
        for item_id in item_ids:
            print(f"  - {item_id}")
        if not typer.confirm("This action cannot be undone. Continue?"):
            raise typer.Exit()
    
    from omnifocus_api.apple_script_client import delete_task, execute_omnifocus_applescript
    
    success_count = 0
    failed_items = []
    
    for item_id in item_ids:
        try:
            if not dry_run:
                if item_type == "tasks":
                    if delete_task(item_id):
                        success_count += 1
                        print(f"✅ Deleted task: {item_id}")
                    else:
                        failed_items.append(item_id)
                        print(f"❌ Failed to delete task: {item_id}")
                else:  # projects
                    script = f'''
tell application "OmniFocus"
    tell default document
        set targetProject to first flattened project whose id is "{item_id}"
        delete targetProject
    end tell
end tell
'''
                    execute_omnifocus_applescript(script)
                    success_count += 1
                    print(f"✅ Deleted project: {item_id}")
            else:
                print(f"📋 Would delete {item_type[:-1]}: {item_id}")
                success_count += 1
        except Exception as e:
            failed_items.append(item_id)
            print(f"❌ Error deleting {item_type[:-1]} {item_id}: {e}")
    
    print(f"\nSummary: {success_count} {item_type} {'deleted' if not dry_run else 'would be deleted'}")
    if failed_items:
        print(f"Failed {item_type}: {', '.join(failed_items)}")

# === End Bulk Operations ===

@app.command("get-task-ids")
def get_task_ids_command(
    query: str = typer.Argument("", help="Search string to find tasks. If blank, returns all task IDs."),
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Filter to a specific project."),
    status: Optional[str] = typer.Option(None, "--status", "-s", help="Filter by status (Active, Completed, etc.)."),
    flagged_only: bool = typer.Option(False, "--flagged-only", "-f", help="Show only flagged tasks."),
    due_before: Optional[str] = typer.Option(None, "--due-before", help="Filter by due date before YYYY-MM-DD."),
    due_after: Optional[str] = typer.Option(None, "--due-after", help="Filter by due date after YYYY-MM-DD."),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON instead of plain text."),
    file: Optional[str] = typer.Option(get_latest_json_export_path(), "--file", help="Path to the OmniFocus JSON export file."),
):
    """Get task IDs from a query. Useful for bulk operations."""
    if not file:
        print("No export file available. Run 'ofcli ingest' first.", file=sys.stderr)
        raise typer.Exit(code=1)
    
    try:
        prepared_data = load_and_prepare_omnifocus_data(file)
        if not prepared_data:
            print("Failed to load data from export file.", file=sys.stderr)
            raise typer.Exit(code=1)
    except Exception as e:
        print(f"Error loading data: {e}", file=sys.stderr)
        raise typer.Exit(code=1)
    
    # Build filters
    filters = {}
    if project:
        # Find project by name
        project_id = None
        for pid, pdata in prepared_data.get("projects_map", {}).items():
            if pdata.get("name", "").lower() == project.lower():
                project_id = pid
                break
        if project_id:
            filters["project_id_filter"] = project_id
        else:
            print(f"Project '{project}' not found.", file=sys.stderr)
            raise typer.Exit(code=1)
    
    if status:
        filters["status_filter"] = status
    
    if flagged_only:
        # Filter for flagged tasks
        tasks = [t for t in prepared_data.get("all_tasks", []) if t.get("flagged", False)]
    else:
        # Use query_prepared_data
        tasks = query_prepared_data(
            prepared_data,
            "tasks",
            name_filter=query if query else None,
            **filters
        )
    
    # Apply date filters if specified
    if due_before:
        due_before_date = parse_cli_date(due_before)
        if due_before_date:
            tasks = [t for t in tasks if get_item_date(t.get("dueDate")) and get_item_date(t.get("dueDate")) < due_before_date]
    
    if due_after:
        due_after_date = parse_cli_date(due_after)
        if due_after_date:
            tasks = [t for t in tasks if get_item_date(t.get("dueDate")) and get_item_date(t.get("dueDate")) > due_after_date]
    
    if json_output:
        # Output as JSON with task details
        result = []
        for task in tasks:
            result.append({
                "id": task.get("id"),
                "name": task.get("name"),
                "project": prepared_data.get("projects_map", {}).get(task.get("projectId"), {}).get("name", "No Project"),
                "status": task.get("status"),
                "flagged": task.get("flagged", False),
                "dueDate": task.get("dueDate"),
                "deferDate": task.get("deferDate"),
                "completed": task.get("completed", False)
            })
        print(json.dumps(result, indent=2))
    else:
        # Output just the IDs, one per line
        task_ids = [task.get("id") for task in tasks if task.get("id")]
        for task_id in task_ids:
            print(task_id)
        
        if task_ids:
            print(f"\nFound {len(task_ids)} tasks", file=sys.stderr)
        else:
            print("No tasks found matching the criteria.", file=sys.stderr)

@app.command("get-project-ids")
def get_project_ids_command(
    query: str = typer.Argument("", help="Search string to find projects. If blank, returns all project IDs."),
    status: Optional[str] = typer.Option(None, "--status", "-s", help="Filter by status (Active, OnHold, etc.)."),
    folder: Optional[str] = typer.Option(None, "--folder", "-f", help="Filter to a specific folder."),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON instead of plain text."),
    file: Optional[str] = typer.Option(get_latest_json_export_path(), "--file", help="Path to the OmniFocus JSON export file."),
):
    """Get project IDs from a query. Useful for bulk operations."""
    if not file:
        print("No export file available. Run 'ofcli ingest' first.", file=sys.stderr)
        raise typer.Exit(code=1)
    
    try:
        prepared_data = load_and_prepare_omnifocus_data(file)
        if not prepared_data:
            print("Failed to load data from export file.", file=sys.stderr)
            raise typer.Exit(code=1)
    except Exception as e:
        print(f"Error loading data: {e}", file=sys.stderr)
        raise typer.Exit(code=1)
    
    # Build filters
    filters = {}
    if status:
        filters["status_filter"] = status
    
    if folder:
        # Find folder by name
        folder_id = None
        for fid, fdata in prepared_data.get("folders_map", {}).items():
            if fdata.get("name", "").lower() == folder.lower():
                folder_id = fid
                break
        if folder_id:
            filters["folder_id_filter"] = folder_id
        else:
            print(f"Folder '{folder}' not found.", file=sys.stderr)
            raise typer.Exit(code=1)
    
    # Use query_prepared_data
    projects = query_prepared_data(
        prepared_data,
        "projects",
        name_filter=query if query else None,
        **filters
    )
    
    if json_output:
        # Output as JSON with project details
        result = []
        for project in projects:
            result.append({
                "id": project.get("id"),
                "name": project.get("name"),
                "status": project.get("status"),
                "folder": prepared_data.get("folders_map", {}).get(project.get("folderId"), {}).get("name", "No Folder"),
                "completed": project.get("completed", False),
                "dueDate": project.get("dueDate"),
                "deferDate": project.get("deferDate")
            })
        print(json.dumps(result, indent=2))
    else:
        # Output just the IDs, one per line
        project_ids = [project.get("id") for project in projects if project.get("id")]
        for project_id in project_ids:
            print(project_id)
        
        if project_ids:
            print(f"\nFound {len(project_ids)} projects", file=sys.stderr)
        else:
            print("No projects found matching the criteria.", file=sys.stderr)

@app.command("bulk-create")
def bulk_create_command(
    input_file: str = typer.Option(..., "--input", "-i", help="Path to JSON file containing tasks to create."),
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Default project for all tasks (overrides individual task project)."),
    folder: Optional[str] = typer.Option(None, "--folder", "-f", help="Default folder for all tasks (overrides individual task folder)."),
    dry_run: bool = typer.Option(False, "--dry-run", "-n", help="Show what would be created without making changes."),
    force: bool = typer.Option(False, "--force", help="Create without confirmation prompt."),
):
    """Create multiple tasks in bulk from a JSON file."""
    if not os.path.exists(input_file):
        print(f"Input file not found: {input_file}", file=sys.stderr)
        raise typer.Exit(code=1)
    
    try:
        with open(input_file, 'r') as f:
            tasks_data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Invalid JSON in input file: {e}", file=sys.stderr)
        raise typer.Exit(code=1)
    except Exception as e:
        print(f"Error reading input file: {e}", file=sys.stderr)
        raise typer.Exit(code=1)
    
    if not isinstance(tasks_data, list):
        print("Input file must contain a JSON array of tasks.", file=sys.stderr)
        raise typer.Exit(code=1)
    
    if not tasks_data:
        print("No tasks found in input file.", file=sys.stderr)
        raise typer.Exit(code=1)
    
    # Validate task data
    valid_tasks = []
    invalid_tasks = []
    
    for i, task in enumerate(tasks_data):
        if not isinstance(task, dict):
            invalid_tasks.append(f"Task {i}: Not a dictionary")
            continue
        
        if not task.get("title") and not task.get("name"):
            invalid_tasks.append(f"Task {i}: Missing title/name")
            continue
        
        # Normalize task data
        normalized_task = {
            "title": task.get("title") or task.get("name"),
            "note": task.get("note") or task.get("notes", ""),
            "project": task.get("project") or project,
            "folder": task.get("folder") or folder,
            "due_date": task.get("due_date") or task.get("due") or task.get("dueDate"),
            "defer_date": task.get("defer_date") or task.get("defer") or task.get("deferDate"),
            "duration": task.get("duration") or task.get("estimatedMinutes"),
            "tags": task.get("tags", ""),
            "recurrence": task.get("recurrence") or task.get("recurrence_rule")
        }
        
        valid_tasks.append(normalized_task)
    
    if invalid_tasks:
        print("Invalid tasks found:", file=sys.stderr)
        for error in invalid_tasks:
            print(f"  - {error}", file=sys.stderr)
        raise typer.Exit(code=1)
    
    if not force and not dry_run:
        print(f"About to create {len(valid_tasks)} tasks:")
        for task in valid_tasks:
            project_info = f" in project '{task['project']}'" if task['project'] else ""
            folder_info = f" in folder '{task['folder']}'" if task['folder'] else ""
            print(f"  - {task['title']}{project_info}{folder_info}")
        if not typer.confirm("Continue?"):
            raise typer.Exit()
    
    from omnifocus_api.apple_script_client import execute_omnifocus_applescript
    
    success_count = 0
    failed_tasks = []
    
    for i, task in enumerate(valid_tasks):
        try:
            if not dry_run:
                # Build AppleScript for task creation
                script_parts = [
                    'tell application "OmniFocus"',
                    '    tell default document',
                    '        set newTask to make new inbox task with properties {name:"' + task['title'].replace('"', '\\"') + '"}'
                ]
                
                # Add note if provided
                if task['note']:
                    script_parts.append('        set note of newTask to "' + task['note'].replace('"', '\\"').replace('\n', '\\n') + '"')
                
                # Add due date if provided
                if task['due_date']:
                    # Convert YYYY-MM-DD format to AppleScript date format
                    try:
                        from datetime import datetime
                        date_obj = datetime.strptime(task['due_date'], "%Y-%m-%d")
                        applescript_date = date_obj.strftime("%B %d, %Y 00:00:00")
                        script_parts.append('        set due date of newTask to date "' + applescript_date + '"')
                    except ValueError:
                        # Fallback to original format if parsing fails
                        script_parts.append('        set due date of newTask to date "' + task['due_date'] + '"')
                
                # Add defer date if provided
                if task['defer_date']:
                    # Convert YYYY-MM-DD format to AppleScript date format
                    try:
                        from datetime import datetime
                        date_obj = datetime.strptime(task['defer_date'], "%Y-%m-%d")
                        applescript_date = date_obj.strftime("%B %d, %Y 00:00:00")
                        script_parts.append('        set defer date of newTask to date "' + applescript_date + '"')
                    except ValueError:
                        # Fallback to original format if parsing fails
                        script_parts.append('        set defer date of newTask to date "' + task['defer_date'] + '"')
                
                # Add estimated duration if provided
                if task['duration']:
                    script_parts.append('        set estimated minutes of newTask to ' + str(task['duration']))
                
                # Add recurrence if provided
                if task['recurrence']:
                    script_parts.append('        set repetition of newTask to repetition rule "' + task['recurrence'] + '"')
                
                # Move to project if specified
                if task['project']:
                    script_parts.extend([
                        '        set targetProject to first flattened project whose name is "' + task['project'].replace('"', '\\"') + '"',
                        '        if targetProject is not missing value then',
                        '            move newTask to targetProject',
                        '        end if'
                    ])
                
                # Move to folder if specified (and no project)
                elif task['folder']:
                    script_parts.extend([
                        '        set targetFolder to first flattened folder whose name is "' + task['folder'].replace('"', '\\"') + '"',
                        '        if targetFolder is not missing value then',
                        '            set newProject to make new project with properties {name:"' + task['title'].replace('"', '\\"') + '"}',
                        '            move newProject to targetFolder',
                        '            move newTask to newProject',
                        '        end if'
                    ])
                
                script_parts.extend([
                    '        return id of newTask',
                    '    end tell',
                    'end tell'
                ])
                
                script = '\n'.join(script_parts)
                result = execute_omnifocus_applescript(script)
                
                success_count += 1
                print(f"✅ Created task: {task['title']} (ID: {result.strip()})")
            else:
                print(f"📋 Would create task: {task['title']}")
                success_count += 1
                
        except Exception as e:
            failed_tasks.append(f"{task['title']}: {str(e)}")
            print(f"❌ Error creating task '{task['title']}': {e}")
    
    print(f"\nSummary: {success_count} tasks {'created' if not dry_run else 'would be created'}")
    if failed_tasks:
        print(f"Failed tasks:")
        for failed in failed_tasks:
            print(f"  - {failed}")

@app.command("bulk-create-from-csv")
def bulk_create_from_csv_command(
    input_file: str = typer.Option(..., "--input", "-i", help="Path to CSV file containing tasks to create."),
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Default project for all tasks."),
    folder: Optional[str] = typer.Option(None, "--folder", "-f", help="Default folder for all tasks."),
    dry_run: bool = typer.Option(False, "--dry-run", "-n", help="Show what would be created without making changes."),
    force: bool = typer.Option(False, "--force", help="Create without confirmation prompt."),
):
    """Create multiple tasks in bulk from a CSV file."""
    if not os.path.exists(input_file):
        print(f"Input file not found: {input_file}", file=sys.stderr)
        raise typer.Exit(code=1)
    
    try:
        import csv
        with open(input_file, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            tasks_data = list(reader)
    except Exception as e:
        print(f"Error reading CSV file: {e}", file=sys.stderr)
        raise typer.Exit(code=1)
    
    if not tasks_data:
        print("No tasks found in CSV file.", file=sys.stderr)
        raise typer.Exit(code=1)
    
    # Convert CSV data to the same format as JSON
    valid_tasks = []
    invalid_tasks = []
    
    for i, task in enumerate(tasks_data):
        # Check for required fields
        title = task.get("title") or task.get("name") or task.get("Title") or task.get("Name")
        if not title:
            invalid_tasks.append(f"Row {i+1}: Missing title/name")
            continue
        
        # Normalize task data
        normalized_task = {
            "title": title,
            "note": task.get("note") or task.get("notes") or task.get("Note") or task.get("Notes", ""),
            "project": task.get("project") or task.get("Project") or project,
            "folder": task.get("folder") or task.get("Folder") or folder,
            "due_date": task.get("due_date") or task.get("due") or task.get("Due") or task.get("dueDate") or task.get("DueDate"),
            "defer_date": task.get("defer_date") or task.get("defer") or task.get("Defer") or task.get("deferDate") or task.get("DeferDate"),
            "duration": task.get("duration") or task.get("Duration") or task.get("estimatedMinutes"),
            "tags": task.get("tags") or task.get("Tags", ""),
            "recurrence": task.get("recurrence") or task.get("Recurrence") or task.get("recurrence_rule")
        }
        
        valid_tasks.append(normalized_task)
    
    if invalid_tasks:
        print("Invalid tasks found:", file=sys.stderr)
        for error in invalid_tasks:
            print(f"  - {error}", file=sys.stderr)
        raise typer.Exit(code=1)
    
    if not force and not dry_run:
        print(f"About to create {len(valid_tasks)} tasks from CSV:")
        for task in valid_tasks:
            project_info = f" in project '{task['project']}'" if task['project'] else ""
            folder_info = f" in folder '{task['folder']}'" if task['folder'] else ""
            print(f"  - {task['title']}{project_info}{folder_info}")
        if not typer.confirm("Continue?"):
            raise typer.Exit()
    
    from omnifocus_api.apple_script_client import execute_omnifocus_applescript
    
    success_count = 0
    failed_tasks = []
    
    for i, task in enumerate(valid_tasks):
        try:
            if not dry_run:
                # Build AppleScript for task creation (same as JSON version)
                script_parts = [
                    'tell application "OmniFocus"',
                    '    tell default document',
                    '        set newTask to make new inbox task with properties {name:"' + task['title'].replace('"', '\\"') + '"}'
                ]
                
                # Add note if provided
                if task['note']:
                    script_parts.append('        set note of newTask to "' + task['note'].replace('"', '\\"').replace('\n', '\\n') + '"')
                
                # Add due date if provided
                if task['due_date']:
                    # Convert YYYY-MM-DD format to AppleScript date format
                    try:
                        from datetime import datetime
                        date_obj = datetime.strptime(task['due_date'], "%Y-%m-%d")
                        applescript_date = date_obj.strftime("%B %d, %Y 00:00:00")
                        script_parts.append('        set due date of newTask to date "' + applescript_date + '"')
                    except ValueError:
                        # Fallback to original format if parsing fails
                        script_parts.append('        set due date of newTask to date "' + task['due_date'] + '"')
                
                # Add defer date if provided
                if task['defer_date']:
                    # Convert YYYY-MM-DD format to AppleScript date format
                    try:
                        from datetime import datetime
                        date_obj = datetime.strptime(task['defer_date'], "%Y-%m-%d")
                        applescript_date = date_obj.strftime("%B %d, %Y 00:00:00")
                        script_parts.append('        set defer date of newTask to date "' + applescript_date + '"')
                    except ValueError:
                        # Fallback to original format if parsing fails
                        script_parts.append('        set defer date of newTask to date "' + task['defer_date'] + '"')
                
                # Add estimated duration if provided
                if task['duration']:
                    script_parts.append('        set estimated minutes of newTask to ' + str(task['duration']))
                
                # Add recurrence if provided
                if task['recurrence']:
                    script_parts.append('        set repetition of newTask to repetition rule "' + task['recurrence'] + '"')
                
                # Move to project if specified
                if task['project']:
                    script_parts.extend([
                        '        set targetProject to first flattened project whose name is "' + task['project'].replace('"', '\\"') + '"',
                        '        if targetProject is not missing value then',
                        '            move newTask to targetProject',
                        '        end if'
                    ])
                
                # Move to folder if specified (and no project)
                elif task['folder']:
                    script_parts.extend([
                        '        set targetFolder to first flattened folder whose name is "' + task['folder'].replace('"', '\\"') + '"',
                        '        if targetFolder is not missing value then',
                        '            set newProject to make new project with properties {name:"' + task['title'].replace('"', '\\"') + '"}',
                        '            move newProject to targetFolder',
                        '            move newTask to newProject',
                        '        end if'
                    ])
                
                script_parts.extend([
                    '        return id of newTask',
                    '    end tell',
                    'end tell'
                ])
                
                script = '\n'.join(script_parts)
                result = execute_omnifocus_applescript(script)
                
                success_count += 1
                print(f"✅ Created task: {task['title']} (ID: {result.strip()})")
            else:
                print(f"📋 Would create task: {task['title']}")
                success_count += 1
                
        except Exception as e:
            failed_tasks.append(f"{task['title']}: {str(e)}")
            print(f"❌ Error creating task '{task['title']}': {e}")
    
    print(f"\nSummary: {success_count} tasks {'created' if not dry_run else 'would be created'} from CSV")
    if failed_tasks:
        print(f"Failed tasks:")
        for failed in failed_tasks:
            print(f"  - {failed}")



if __name__ == "__main__":
    app() 