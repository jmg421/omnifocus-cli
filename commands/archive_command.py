import json
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.data_loading import load_and_prepare_omnifocus_data, get_latest_json_export_path

def ensure_archive_directory():
    """Ensure the reference_archive directory exists."""
    archive_dir = "reference_archive"
    if not os.path.exists(archive_dir):
        os.makedirs(archive_dir)
        print(f"Created archive directory: {archive_dir}")
    return archive_dir

def is_item_archivable(item: Dict[str, Any], item_type: str, age_days: int = 0) -> bool:
    """
    Determine if an item should be archived.
    
    Args:
        item: Task or project dictionary
        item_type: "task" or "project"
        age_days: If > 0, only archive items completed this many days ago or more
    
    Returns:
        True if the item should be archived
    """
    # Check completion status
    if item_type == "task":
        # Tasks are archivable if completed
        is_completed = item.get("completed", False) or item.get("status") == "Completed"
    elif item_type == "project":
        # Projects are archivable if done/completed
        is_completed = item.get("status") in ["Done", "Completed"]
    else:
        return False
    
    if not is_completed:
        return False
    
    # If age_days is 0, archive all completed items immediately
    if age_days == 0:
        return True
    
    # TODO: Age-based filtering would require completion dates
    # For now, we'll archive all completed items
    # In the future, we could add completion date tracking
    return True

def create_archive_summary(archived_data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a summary of what was archived."""
    summary = {
        "archive_date": datetime.now().isoformat(),
        "total_tasks_archived": len(archived_data.get("tasks", [])),
        "total_projects_archived": len(archived_data.get("projects", {})),
        "total_inbox_tasks_archived": len(archived_data.get("inboxTasks", [])),
        "tasks_by_project": {},
        "projects_by_status": {}
    }
    
    # Count tasks by project
    for task in archived_data.get("tasks", []):
        project_id = task.get("projectId", "no_project")
        if project_id not in summary["tasks_by_project"]:
            summary["tasks_by_project"][project_id] = 0
        summary["tasks_by_project"][project_id] += 1
    
    # Count projects by status
    for project_id, project in archived_data.get("projects", {}).items():
        status = project.get("status", "unknown")
        if status not in summary["projects_by_status"]:
            summary["projects_by_status"][status] = 0
        summary["projects_by_status"][status] += 1
    
    return summary

def generate_trimmed_export(original_data: Dict[str, Any], archived_items: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate a trimmed export with archived items removed.
    
    Args:
        original_data: The original export data
        archived_items: Items that were archived
    
    Returns:
        Trimmed export data
    """
    archived_task_ids = {task["id"] for task in archived_items.get("tasks", [])}
    archived_project_ids = set(archived_items.get("projects", {}).keys())
    archived_inbox_task_ids = {task["id"] for task in archived_items.get("inboxTasks", [])}
    
    # Create trimmed data
    trimmed_data = {
        "version": original_data.get("version", "unknown"),
        "timestamp": datetime.now().isoformat(),
        "tasks": [],
        "projects": {},
        "inboxTasks": [],
        "folders": original_data.get("folders", {}),  # Keep all folders
        "tags": original_data.get("tags", {}),        # Keep all tags
        "taskTags": original_data.get("taskTags", {}) # Keep all tag mappings
    }
    
    # Filter tasks
    for task in original_data.get("tasks", []):
        if task["id"] not in archived_task_ids:
            # Also exclude tasks that belong to archived projects
            if task.get("projectId") not in archived_project_ids:
                trimmed_data["tasks"].append(task)
    
    # Filter projects
    for project_id, project in original_data.get("projects", {}).items():
        if project_id not in archived_project_ids:
            trimmed_data["projects"][project_id] = project
    
    # Filter inbox tasks
    for task in original_data.get("inboxTasks", []):
        if task["id"] not in archived_inbox_task_ids:
            trimmed_data["inboxTasks"].append(task)
    
    return trimmed_data

def handle_archive_completed(args):
    """
    Archive completed/old OmniFocus content.
    
    Args:
        args: Arguments object with:
            - file: Optional path to export file
            - age_days: Optional minimum age in days for archiving
            - dry_run: If True, don't actually archive, just show what would be archived
            - force: If True, don't prompt for confirmation
    """
    # Get export file
    file_path = getattr(args, 'file', None) or get_latest_json_export_path()
    if not file_path:
        print("Error: No export file found", file=sys.stderr)
        return
    
    # Get options
    age_days = getattr(args, 'age_days', 0)
    dry_run = getattr(args, 'dry_run', False)
    force = getattr(args, 'force', False)
    
    print(f"Loading OmniFocus data from: {file_path}")
    
    # Load data
    original_data = {}
    try:
        with open(file_path, 'r') as f:
            original_data = json.load(f)
    except Exception as e:
        print(f"Error loading export file: {e}", file=sys.stderr)
        return
    
    # Find archivable items
    archivable_tasks = []
    archivable_inbox_tasks = []
    archivable_projects = {}
    
    # Check tasks
    for task in original_data.get("tasks", []):
        if is_item_archivable(task, "task", age_days):
            archivable_tasks.append(task)
    
    # Check inbox tasks
    for task in original_data.get("inboxTasks", []):
        if is_item_archivable(task, "task", age_days):
            archivable_inbox_tasks.append(task)
    
    # Check projects
    for project_id, project in original_data.get("projects", {}).items():
        if is_item_archivable(project, "project", age_days):
            archivable_projects[project_id] = project
    
    # Show summary
    total_archivable = len(archivable_tasks) + len(archivable_inbox_tasks) + len(archivable_projects)
    
    if total_archivable == 0:
        print("No completed items found to archive.")
        return
    
    print(f"\n=== Archive Summary ===")
    print(f"Completed tasks to archive: {len(archivable_tasks)}")
    print(f"Completed inbox tasks to archive: {len(archivable_inbox_tasks)}")
    print(f"Completed projects to archive: {len(archivable_projects)}")
    print(f"Total items to archive: {total_archivable}")
    
    # Calculate remaining items
    remaining_tasks = len(original_data.get("tasks", [])) - len(archivable_tasks)
    remaining_inbox = len(original_data.get("inboxTasks", [])) - len(archivable_inbox_tasks)
    remaining_projects = len(original_data.get("projects", {})) - len(archivable_projects)
    
    print(f"\nAfter archiving:")
    print(f"Active tasks: {remaining_tasks}")
    print(f"Active inbox tasks: {remaining_inbox}")  
    print(f"Active projects: {remaining_projects}")
    print(f"Total active items: {remaining_tasks + remaining_inbox + remaining_projects}")
    
    reduction_percent = (total_archivable / (total_archivable + remaining_tasks + remaining_inbox + remaining_projects)) * 100
    print(f"Data reduction: {reduction_percent:.1f}%")
    
    if dry_run:
        print("\n[DRY RUN] No changes made.")
        return
    
    # Confirm action
    if not force:
        response = input(f"\nArchive {total_archivable} completed items? (y/N): ")
        if response.lower() != 'y':
            print("Archive cancelled.")
            return
    
    # Ensure archive directory exists
    archive_dir = ensure_archive_directory()
    
    # Create archived data structure
    archived_data = {
        "version": original_data.get("version", "unknown"),
        "archive_date": datetime.now().isoformat(),
        "source_file": file_path,
        "tasks": archivable_tasks,
        "inboxTasks": archivable_inbox_tasks,
        "projects": archivable_projects,
        "folders": original_data.get("folders", {}),  # Include folders for context
        "tags": original_data.get("tags", {})         # Include tags for context
    }
    
    # Generate archive filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    archive_file = os.path.join(archive_dir, f"omnifocus_archive_{timestamp}.json")
    
    # Save archive
    try:
        with open(archive_file, 'w') as f:
            json.dump(archived_data, f, indent=2)
        print(f"✅ Archive saved to: {archive_file}")
    except Exception as e:
        print(f"Error saving archive: {e}", file=sys.stderr)
        return
    
    # Generate trimmed export
    trimmed_data = generate_trimmed_export(original_data, archived_data)
    
    # Save trimmed export
    base_name = os.path.splitext(file_path)[0]
    trimmed_file = f"{base_name}_active.json"
    
    try:
        with open(trimmed_file, 'w') as f:
            json.dump(trimmed_data, f, indent=2)
        print(f"✅ Active data saved to: {trimmed_file}")
    except Exception as e:
        print(f"Error saving trimmed export: {e}", file=sys.stderr)
        return
    
    # Create and save summary
    summary = create_archive_summary(archived_data)
    summary_file = os.path.join(archive_dir, f"archive_summary_{timestamp}.json")
    
    try:
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        print(f"✅ Archive summary saved to: {summary_file}")
    except Exception as e:
        print(f"Warning: Could not save archive summary: {e}")
    
    print(f"\n🎉 Archive complete!")
    print(f"📂 Archived: {total_archivable} completed items")
    print(f"⚡ Active dataset reduced by {reduction_percent:.1f}%")
    print(f"🔍 Use the trimmed export for faster queries: {trimmed_file}") 