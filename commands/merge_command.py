"""
Handles the logic for the 'merge-projects' command.
"""
import subprocess
import shlex # For safely formatting arguments in shell commands

def generate_merge_applescript(source_id: str, target_id: str, delete_source: bool) -> str:
    """Generates the AppleScript to merge tasks from source project to target project."""
    
    # Convert Python bool to AppleScript boolean
    delete_source_applescript = "true" if delete_source else "false"

    script = f"""
tell application "OmniFocus"
    tell default document
        set sourceProjectId to "{source_id}"
        set targetProjectId to "{target_id}"
        set deleteSourceBool to {delete_source_applescript}

        try
            set sourceProject to first flattened project whose id is sourceProjectId
        on error
            return "Error: Source project with ID '" & sourceProjectId & "' not found."
        end try

        try
            set targetProject to first flattened project whose id is targetProjectId
        on error
            return "Error: Target project with ID '" & targetProjectId & "' not found."
        end try

        if name of sourceProject is missing value then
             return "Error: Source project with ID '" & sourceProjectId & "' not found (missing value)."
        end if
        if name of targetProject is missing value then
            return "Error: Target project with ID '" & targetProjectId & "' not found (missing value)."
        end if

        -- Move tasks
        -- It's often safer to iterate over a static list of task IDs or references
        -- as modifying the collection while iterating can sometimes lead to issues.
        -- However, for moving, OmniFocus usually handles this well.
        -- We'll collect task references first.
        set tasksToMove to every task of sourceProject
        
        if (count of tasksToMove) is 0 then
            if deleteSourceBool is true then
                delete sourceProject
                return "Source project '{source_id}' was empty. Deleted source project. No tasks to move."
            else
                return "Source project '{source_id}' was empty. No tasks to move. Source project not deleted."
            end if
        end if
        
        repeat with aTask in tasksToMove
            -- Move the task to the target project.
            -- 'move' changes the containing project.
            -- Adding to 'tasks of targetProject' effectively moves it.
            move aTask to end of tasks of targetProject
        end repeat

        set movedTasksCount to (count of tasksToMove)

        -- Optionally delete source project
        if deleteSourceBool is true then
            -- Ensure all tasks were indeed moved out.
            if (count of tasks of sourceProject) is 0 then
                delete sourceProject
                return "Successfully moved " & movedTasksCount & " task(s) from project '" & sourceProjectId & "' to '" & targetProjectId & "'. Source project deleted."
            else
                return "Successfully moved " & movedTasksCount & " task(s). However, source project '" & sourceProjectId & "' was not empty after attempted move and was NOT deleted. Please check manually."
            end if
        else
            return "Successfully moved " & movedTasksCount & " task(s) from project '" & sourceProjectId & "' to '" & targetProjectId & "'. Source project not deleted."
        end if
    end tell
end tell
    """
    return script

def handle_merge_projects(args):
    """
    Handles the merging of two projects.
    args must have 'source_id', 'target_id', and 'delete_source' attributes.
    """
    source_id = args.source_id
    target_id = args.target_id
    delete_source = args.delete_source

    if not source_id or not target_id:
        print("Error: Source ID and Target ID must be provided.")
        return

    print(f"Preparing to merge tasks from project ID '{source_id}' into project ID '{target_id}'.")
    if delete_source:
        print(f"Source project '{source_id}' will be deleted after successful merge.")
    
    applescript_command = generate_merge_applescript(source_id, target_id, delete_source)
    
    print("\nGenerated AppleScript (for review):")
    print("------------------------------------")
    print(applescript_command)
    print("------------------------------------\n")

    execute_omnifocus_applescript = None
    try:
        from omnifocus_api.apple_script_client import execute_omnifocus_applescript
    except ImportError:
        print("Info: Could not import 'execute_omnifocus_applescript' from 'omnifocus_api.apple_script_client'.")
        print("Will use direct 'osascript' call as a fallback.")
    except Exception as e_import_other:
        print(f"An unexpected error occurred during import attempt: {e_import_other}")
        print("Will use direct 'osascript' call as a fallback.")

    try:
        if execute_omnifocus_applescript:
            print("Attempting to execute AppleScript via 'execute_omnifocus_applescript'...")
            result = execute_omnifocus_applescript(applescript_command)
            print(f"OmniFocus AppleScript execution successful via imported function.")
            print(f"Result: {result}")
            if "Error:" in result:
                 print(f"Operation reported an error: {result}")
        else:
            # Fallback to direct osascript call
            print("Attempting to execute AppleScript via direct 'osascript' call...")
            cmd = ["osascript", "-e", applescript_command]
            process = subprocess.run(cmd, capture_output=True, text=True, check=False)

            if process.returncode == 0:
                result = process.stdout.strip()
                print(f"OmniFocus AppleScript execution (via osascript fallback) successful.")
                print(f"Result: {result}")
                if "Error:" in result:
                    print(f"Operation reported an error: {result}")
            else:
                error_message = process.stderr.strip()
                print(f"Error executing AppleScript with osascript (fallback):")
                print(error_message)
                return # Stop on error

        # Common post-execution steps
        print("\nIMPORTANT: OmniFocus data has been changed (or an attempt was made). ")
        print("Review the results above. If successful, re-export your OmniFocus data to update 'data/omnifocus_export.json' for future queries.")
            
    except Exception as e:
        print(f"An unexpected error occurred during AppleScript execution: {e}") 