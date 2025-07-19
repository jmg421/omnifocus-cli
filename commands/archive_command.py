import json
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from omnifocus_api.apple_script_client import execute_omnifocus_applescript  # Unified runner helper
from ..utils.data_loading import load_and_prepare_omnifocus_data, get_latest_json_export_path

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

def delete_items_from_omnifocus(items_to_delete: List[Dict[str, Any]], item_type: str) -> bool:
    """
    Delete archived items from the live OmniFocus database using AppleScript.
    
    Args:
        items_to_delete: List of task or project dictionaries to delete
        item_type: "tasks" or "projects"
    
    Returns:
        True if deletion was successful, False otherwise
    """
    if not items_to_delete:
        return True
    
    # Build AppleScript to delete items
    item_ids = [item["id"] for item in items_to_delete]
    
    # Process items in very small batches to avoid system hangs
    batch_size = 10
    total_deleted = 0
    
    print(f"  Processing {len(item_ids)} {item_type} in batches of {batch_size}...")
    
    for i in range(0, len(item_ids), batch_size):
        batch_ids = item_ids[i:i + batch_size]
        batch_num = i // batch_size + 1
        total_batches = (len(item_ids) + batch_size - 1) // batch_size
        
        print(f"  Processing batch {batch_num}/{total_batches}...")
        
        # Add a small delay between batches to prevent overwhelming the system
        if i > 0:
            import time
            time.sleep(0.5)
        
        # Build AppleScript string with ID list
        id_list = "{" + ", ".join(f'\"{id_}\"' for id_ in batch_ids) + "}"

        applescript = f'''tell application "OmniFocus"
    tell default document
        set deletedCount to 0
        set itemList to {id_list}
        repeat with itemID in itemList
            try
                if "{item_type}" is "tasks" then
                    set targetItem to first flattened task whose id is itemID
                else
                    set targetItem to first project whose id is itemID
                end if
                delete targetItem
                set deletedCount to deletedCount + 1
            on error
                -- Item might already be deleted or not found, continue
            end try
        end repeat
        return deletedCount
    end tell
end tell'''

        try:
            result_str = execute_omnifocus_applescript(applescript)
            batch_deleted = int(result_str) if result_str.isdigit() else 0
            total_deleted += batch_deleted
            if batch_num % 10 == 0 or batch_num == total_batches:
                print(f"  ✅ Progress: {total_deleted} {item_type} deleted ({batch_num}/{total_batches} batches)")
        except Exception as e:
            print(f"  ❌ Error executing AppleScript batch: {e}")
            return False
    
    print(f"✅ Successfully deleted {total_deleted} {item_type} from OmniFocus")
    return True

def handle_archive_completed(args):
    """
    Archive completed/old OmniFocus content.
    
    Args:
        args: Arguments object with:
            - file: Optional path to export file
            - age_days: Optional minimum age in days for archiving
            - dry_run: If True, don't actually archive, just show what would be archived
            - force: If True, don't prompt for confirmation
            - delete_from_omnifocus: If True, also delete archived items from live OmniFocus database
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
    delete_from_omnifocus = getattr(args, 'delete_from_omnifocus', False)
    
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
        if delete_from_omnifocus:
            print("[DRY RUN] Would also delete archived items from live OmniFocus database.")
        return
    
    # Confirm action
    if not force:
        if delete_from_omnifocus:
            print(f"\n⚠️  WARNING: This will PERMANENTLY DELETE {total_archivable} completed items from your live OmniFocus database!")
            print("   The items will be safely archived first, but this action cannot be undone.")
            response = input(f"\nArchive and DELETE {total_archivable} completed items from OmniFocus? (y/N): ")
        else:
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
    
    # Delete archived items from live OmniFocus database if requested
    if delete_from_omnifocus:
        print(f"\n🗑️  Deleting archived items from live OmniFocus database...")
        
        # Delete tasks (including inbox tasks)
        all_archived_tasks = archivable_tasks + archivable_inbox_tasks
        if all_archived_tasks:
            tasks_deleted = delete_items_from_omnifocus(all_archived_tasks, "tasks")
        else:
            tasks_deleted = True
            
        # Delete projects
        if archivable_projects:
            projects_deleted = delete_items_from_omnifocus(list(archivable_projects.values()), "projects")
        else:
            projects_deleted = True
        
        if tasks_deleted and projects_deleted:
            print(f"✅ Successfully cleaned up OmniFocus database")
            print(f"💡 Next export will only contain active items!")
        else:
            print(f"⚠️  Some items may not have been deleted from OmniFocus")
            print(f"   Archive files are still safe - you can retry deletion later")

    print(f"\n🎉 Archive complete!")
    print(f"📂 Archived: {total_archivable} completed items")
    print(f"⚡ Active dataset reduced by {reduction_percent:.1f}%")
    print(f"🔍 Use the trimmed export for faster queries: {trimmed_file}")
    
    if delete_from_omnifocus:
        print(f"🗑️  Live OmniFocus database cleaned up - next export will be optimal!") 