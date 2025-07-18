"""
Handles the logic for the 'delete-project' and potentially other delete commands.
"""
from typing import Optional
from omnifocus_api.apple_script_client import execute_omnifocus_applescript  # Unified runner helper

def generate_delete_project_applescript(project_id: str) -> str:
    """Generates AppleScript to delete a project by its ID."""
    script = f"""
    tell application "OmniFocus"
        tell default document
            try
                set projectToDelete to first flattened project whose id is "{project_id}"
                if name of projectToDelete is not missing value then -- Check if project was found
                    delete projectToDelete
                    return "Project with ID '{project_id}' deleted successfully."
                else
                    -- This path might not be reached if 'first flattened project' errors out first
                    return "Error: Project with ID '{project_id}' not found (name was missing value)."
                end if
            on error errMsg number errNum
                if errNum is -1728 then -- Element not found error (e.g., can't get project)
                    return "Error: Project with ID '{project_id}' not found. (errNum: " & errNum & ")"
                else
                    return "Error deleting project '{project_id}': " & errMsg & " (Num: " & errNum & ")"
                end if
            end try
        end tell
    end tell
    """
    return script

def handle_delete_project(args):
    """Handles deletion of a project."""
    project_id = args.project_id

    if not project_id:
        print("Error: Project ID must be provided.")
        return

    print(f"Preparing to delete project with ID '{project_id}'. This action is permanent.")
    # It might be good to add a confirmation prompt here in a real CLI.
    # For now, we proceed directly.

    applescript_command = generate_delete_project_applescript(project_id)

    print("\nGenerated AppleScript for delete-project (for review):")
    print("------------------------------------")
    print(applescript_command)
    print("------------------------------------\n")

    try:
        print("Executing AppleScript via unified helper…")
        result = execute_omnifocus_applescript(applescript_command)
        
        print(f"OmniFocus AppleScript execution result:")
        print(result)
        if not result.startswith("Error:"):
            print("\nIMPORTANT: OmniFocus data has been changed. Re-export if needed for JSON queries.")

    except Exception as e:
        print(f"An unexpected error occurred during AppleScript execution: {e}")

def generate_delete_task_applescript(task_id: str) -> str:
    """Generates AppleScript to delete a task by its ID, using flattened task lookup."""
    script = f"""
    tell application "OmniFocus"
        tell default document
            try
                set taskToDelete to first flattened task whose id is "{task_id}"
                if name of taskToDelete is not missing value then
                    delete taskToDelete
                    return "Task with ID '{task_id}' deleted successfully."
                else
                    return "Error: Task with ID '{task_id}' not found (name was missing value)."
                end if
            on error errMsg number errNum
                if errNum is -1728 then
                    return "Error: Task with ID '{task_id}' not found. (errNum: " & errNum & ")"
                else
                    return "Error deleting task '{task_id}': " & errMsg & " (Num: " & errNum & ")"
                end if
            end try
        end tell
    end tell
    """
    return script

def handle_delete_task(args):
    """Handles deletion of a task."""
    task_id = args.task_id

    if not task_id:
        print("Error: Task ID must be provided.")
        return

    print(f"Preparing to delete task with ID '{task_id}'. This action is permanent.")
    applescript_command = generate_delete_task_applescript(task_id)

    print("\nGenerated AppleScript for delete-task (for review):")
    print("------------------------------------")
    print(applescript_command)
    print("------------------------------------\n")

    try:
        print("Executing AppleScript via unified helper…")
        result = execute_omnifocus_applescript(applescript_command)
        
        print(f"OmniFocus AppleScript execution result:")
        print(result)
        if not result.startswith("Error:"):
            print("\nIMPORTANT: OmniFocus data has been changed. Re-export if needed for JSON queries.")

    except Exception as e:
        print(f"An unexpected error occurred during AppleScript execution: {e}") 