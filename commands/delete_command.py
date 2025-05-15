"""
Handles the logic for the 'delete-project' and potentially other delete commands.
"""
import subprocess
import tempfile
import os
from typing import Optional

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

    execute_omnifocus_applescript = None
    try:
        from ..omnifocus_api.apple_script_client import execute_omnifocus_applescript
    except ImportError:
        print("Info: Could not import 'execute_omnifocus_applescript'. Using direct 'osascript' call.")

    try:
        if execute_omnifocus_applescript:
            print("Attempting to execute AppleScript via imported function...")
            result = execute_omnifocus_applescript(applescript_command)
        else:
            print("Attempting to execute AppleScript via direct 'osascript' call (using temp file)...")
            tmp_file_path = None
            try:
                with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.applescript') as tmp_script_file:
                    tmp_script_file.write(applescript_command)
                    tmp_file_path = tmp_script_file.name
                process = subprocess.run(["osascript", tmp_file_path], capture_output=True, text=True, check=False)
                if process.returncode == 0:
                    result = process.stdout.strip()
                else:
                    result = f"Error: osascript failed with temp file. STDERR: {process.stderr.strip()}"
            finally:
                if tmp_file_path and os.path.exists(tmp_file_path):
                    os.remove(tmp_file_path)
        
        print(f"OmniFocus AppleScript execution result:")
        print(result)
        if not result.startswith("Error:"):
            print("\nIMPORTANT: OmniFocus data has been changed. Re-export if needed for JSON queries.")

    except Exception as e:
        print(f"An unexpected error occurred during AppleScript execution: {e}") 