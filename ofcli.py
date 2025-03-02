#!/usr/bin/env python3
import sys
import os
import typer
from typing import Optional
from utils import load_env_vars

# Load environment variables
load_env_vars()

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
    json_output: bool = typer.Option(False, "--json", help="Output in JSON format."),
):
    """List tasks or projects from OmniFocus."""
    args = type('Args', (), {
        'project': project,
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

if __name__ == "__main__":
    app() 