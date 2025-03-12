#!/usr/bin/env python3
import sys
import os
import typer
from typing import Optional
from utils import load_env_vars
from enum import Enum
from omnifocus_api import test_evernote_export

# Load environment variables
load_env_vars()

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
from commands.add_command import handle_add
from commands.list_command import handle_list
from commands.complete_command import handle_complete
from commands.prioritize_command import handle_prioritize
from commands.delegation_command import handle_delegation
from commands.audit_command import handle_audit
from commands.calendar_command import handle_calendar
from commands.imessage_command import handle_imessage
from commands.scan_command import handle_scan
from commands.cleanup_command import handle_cleanup
from commands.search_command import handle_search

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
):
    """Use AI to prioritize tasks in OmniFocus."""
    args = type('Args', (), {
        'project': project,
        'limit': limit
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

if __name__ == "__main__":
    app() 