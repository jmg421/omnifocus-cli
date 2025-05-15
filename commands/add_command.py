from ..omnifocus_api import apple_script_client
from ..ai_integration.utils.format_utils import parse_date_string
import subprocess # For the fallback osascript execution
from typing import Optional # Added import for Optional
import tempfile # Added for temporary file
import os # Added for file operations
from datetime import datetime # Keep this
from dateutil.relativedelta import relativedelta # For robust date calculation

def handle_add(args):
    """
    Creates a new task in OmniFocus with the provided arguments.
    """
    title = args.title
    project = args.project
    note = args.note or ""
    due_date = parse_date_string(args.due) if args.due else None

    success, of_task_id = apple_script_client.create_task_via_applescript(
        title=title,
        project_name=project,
        note=note,
        due_date=due_date
    )

    if success:
        print(f"Task '{title}' created in OmniFocus (ID: {of_task_id}).")
    else:
        print(f"Failed to create task '{title}' in OmniFocus.")

def escape_applescript_string(s: str) -> str:
    if not s: return ""
    # Order matters: backslash first, then double quote
    return s.replace('\\', '\\\\').replace('"', '\\"')

def generate_add_detailed_task_applescript(
    title: str,
    folder_name: Optional[str],
    project_name: Optional[str],
    note: Optional[str],
    due_date_str: Optional[str],
    defer_date_str: Optional[str],
    recurrence_rule_str: Optional[str]
) -> str:
    script_parts = []
    script_parts.append('tell application "OmniFocus"')
    script_parts.append('    tell default document')
    # taskCreationTarget is defined and used if targeting a specific folder/project for task creation.
    # newTask is the variable for the task once created.

    s_title = escape_applescript_string(title)
    task_properties_line = f'{{name:"{s_title}"}}' 

    s_folder_name = escape_applescript_string(folder_name) if folder_name else None
    s_project_name = escape_applescript_string(project_name) if project_name else None

    if s_folder_name:
        # This logic is still flawed for adding tasks directly to folders.
        # Tasks should go into projects or the inbox.
        # For this attempt, we'll assume this path might lead to an error or be unused if --project is preferred.
        script_parts.append('        try')
        script_parts.append(f'            set folderRef to first folder whose name is "{s_folder_name}"')
        # The following line is problematic: tasks are not typically made directly in folders this way.
        # script_parts.append(f'            set newTask to make new task with properties {task_properties_line} in folderRef') 
        script_parts.append('        on error')
        script_parts.append(f"            return \"Error: Target folder '{s_folder_name}' not found or cannot create task in folder directly.\"")
        script_parts.append('        end try')
        # If we intended to create in a project *within* a folder, that needs different logic.
        # For now, if --folder is used, it might be better to default to inbox or require a project.
        # To avoid further errors on this path for now, let's make it create in inbox if only folder is specified.
        # This is a temporary simplification for the --folder path:
        script_parts.append(f'        set newTask to make new task with properties {task_properties_line}') 
        print(f"Warning: --folder '{s_folder_name}' specified without --project. Task will be created in Inbox. Folder targeting for loose tasks needs review.")

    elif s_project_name:
        script_parts.append('        try')
        script_parts.append(f'            set projectRef to first flattened project whose name is "{s_project_name}"')
        script_parts.append('        on error')
        script_parts.append(f"            return \"Error: Target project '{s_project_name}' not found.\"")
        script_parts.append('        end try')
        script_parts.append('        tell projectRef') # Create task within the project context
        script_parts.append(f'            set newTask to make new task with properties {task_properties_line}')
        script_parts.append('        end tell')
    else: # Inbox
        script_parts.append(f'        set newTask to make new task with properties {task_properties_line}')

    # Set other properties on newTask
    s_note = escape_applescript_string(note) if note else None
    if s_note:
        script_parts.append(f'        set note of newTask to "{s_note}"')
    if due_date_str:
        script_parts.append(f'        set due date of newTask to date "{due_date_str}"')
    if defer_date_str:
        script_parts.append(f'        set defer date of newTask to date "{defer_date_str}"')
    
    if recurrence_rule_str and recurrence_rule_str.upper() == "FREQ=MONTHLY;INTERVAL=1":
        print(f"Info: For task '{s_title}', please set monthly recurrence manually in OmniFocus UI after creation.")
    elif recurrence_rule_str: 
        s_recurrence_rule_str = escape_applescript_string(recurrence_rule_str)
        script_parts.append('        try')
        script_parts.append(f'            set repetition rule of newTask to (make new repetition rule with properties {{repetition method:fixed interval, rule string:"{s_recurrence_rule_str}"}})')
        script_parts.append('        on error errMsg number errNum')
        script_parts.append(f"            return \"Error setting recurrence ('{s_recurrence_rule_str}'): \" & errMsg & \" (Num: \" & errNum & \")\"")
        script_parts.append('        end try')
        print(f"Warning: Attempted to set recurrence '{s_recurrence_rule_str}'. Verify in OmniFocus.")

    script_parts.append('        return id of newTask')
    script_parts.append('    end tell')
    script_parts.append('end tell')
    
    return "\n".join(script_parts)

def handle_add_detailed_task(args):
    """
    Creates a new task with detailed properties including recurrence.
    """
    title = args.title
    folder_name = args.folder_name
    project_name = args.project_name
    note = args.note
    recurrence_rule_str = args.recurrence_rule

    final_due_date_str = None
    if args.due_date:
        dt_obj = None
        if args.due_date.lower() == "next month 1st":
            now = datetime.now()
            dt_obj = (now.replace(day=1) + relativedelta(months=1))
        elif args.due_date.lower() == "next month 5th":
            now = datetime.now()
            dt_obj = (now.replace(day=1) + relativedelta(months=1)).replace(day=5)
        else:
            parsed_val = parse_date_string(args.due_date) # Assuming this utility exists and works
            if isinstance(parsed_val, datetime):
                dt_obj = parsed_val
            elif isinstance(parsed_val, str):
                 # If parse_date_string returns a string, it means it couldn't parse it to datetime.
                 # We should warn and not try to format it further for AppleScript's `date` command.
                 print(f"Warning: Due date string '{args.due_date}' could not be parsed into a datetime object. Due date may not be set correctly.")
                 final_due_date_str = parsed_val # Pass as is, AppleScript might fail.
            # If parse_date_string returns None, dt_obj remains None
        
        if dt_obj: # If we have a datetime object
            final_due_date_str = dt_obj.strftime("%B %d, %Y %H:%M:%S") # e.g., "June 01, 2025 00:00:00"

    final_defer_date_str = None
    if args.defer_date:
        dt_obj = None
        # Add specific string handling for defer dates if needed, similar to due dates
        parsed_val = parse_date_string(args.defer_date)
        if isinstance(parsed_val, datetime):
            dt_obj = parsed_val
        elif isinstance(parsed_val, str):
            print(f"Warning: Defer date string '{args.defer_date}' could not be parsed into a datetime object. Defer date may not be set correctly.")
            final_defer_date_str = parsed_val

        if dt_obj:
            final_defer_date_str = dt_obj.strftime("%B %d, %Y %H:%M:%S")

    if project_name and folder_name:
        print("Error: Please specify either a project or a folder, not both.")
        return

    applescript_command = generate_add_detailed_task_applescript(
        title, folder_name, project_name, note, 
        final_due_date_str, 
        final_defer_date_str, 
        recurrence_rule_str
    )

    print("\nGenerated AppleScript for add-task (for review):")
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
            task_id_or_error = execute_omnifocus_applescript(applescript_command)
        else:
            print("Attempting to execute AppleScript via direct 'osascript' call (using temp file)...")
            tmp_file_path = None
            try:
                # Create a temporary file to hold the script
                with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.applescript') as tmp_script_file:
                    tmp_script_file.write(applescript_command)
                    tmp_file_path = tmp_script_file.name
                
                process = subprocess.run(["osascript", tmp_file_path], capture_output=True, text=True, check=False)
                
                if process.returncode == 0:
                    task_id_or_error = process.stdout.strip()
                else:
                    task_id_or_error = f"Error: osascript failed with temp file. STDERR: {process.stderr.strip()}"
            finally:
                if tmp_file_path and os.path.exists(tmp_file_path):
                    os.remove(tmp_file_path) # Clean up the temporary file
        
        if task_id_or_error.startswith("Error:"):
            print(f"Failed to create task: {task_id_or_error}")
        else:
            print(f"Task '{title}' created successfully with ID: {task_id_or_error}.")
            print("\nIMPORTANT: OmniFocus data has been changed.")
            print("If this was a recurring task, you might need to re-export your OmniFocus data")
            print("to see all instances if your export method includes future recurring items.")

    except Exception as e:
        print(f"An unexpected error occurred during AppleScript execution: {e}")

def generate_create_project_applescript(project_title: str, folder_name: Optional[str]) -> str:
    """Generates AppleScript to create a new project, optionally in a folder."""
    script_parts = []
    script_parts.append('tell application "OmniFocus"')
    script_parts.append('    tell default document')

    s_project_title = escape_applescript_string(project_title)
    project_properties_line = f'{{name:"{s_project_title}"}}'

    if folder_name:
        s_folder_name = escape_applescript_string(folder_name)
        script_parts.extend([
            '        try',
            f'            set targetFolder to first folder whose name is "{s_folder_name}"',
            '        on error',
            f"            return \"Error: Folder '{s_folder_name}' not found. Project not created.\"",
            '        end try',
            '        tell targetFolder',
            f'            set newProject to make new project with properties {project_properties_line}',
            '        end tell'
        ])
    else:
        script_parts.append(f'        set newProject to make new project with properties {project_properties_line}')
    
    script_parts.extend([
        '        return id of newProject',
        '    end tell',
        'end tell'
    ])
    return "\n".join(script_parts)

def handle_create_project(args):
    """Handles creation of a new project."""
    project_title = args.title
    folder_name = args.folder_name

    applescript_command = generate_create_project_applescript(project_title, folder_name)

    print("\nGenerated AppleScript for create-project (for review):")
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
            item_id_or_error = execute_omnifocus_applescript(applescript_command)
        else:
            print("Attempting to execute AppleScript via direct 'osascript' call (using temp file)...")
            tmp_file_path = None
            try:
                # Create a temporary file to hold the script
                # delete=False is important so we can pass the name to subprocess
                with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.applescript') as tmp_script_file:
                    tmp_script_file.write(applescript_command)
                    tmp_file_path = tmp_script_file.name
                
                # Ensure the file is closed before osascript tries to read it.
                # The 'with' statement handles this automatically on exit from the block.
                process = subprocess.run(["osascript", tmp_file_path], capture_output=True, text=True, check=False)
                
                if process.returncode == 0:
                    item_id_or_error = process.stdout.strip()
                else:
                    item_id_or_error = f"Error: osascript failed with temp file. STDERR: {process.stderr.strip()}"
            finally:
                if tmp_file_path and os.path.exists(tmp_file_path):
                    os.remove(tmp_file_path) # Clean up the temporary file
        
        if item_id_or_error.startswith("Error:"):
            print(f"Failed to create project: {item_id_or_error}")
        else:
            print(f"Project '{project_title}' created successfully with ID: {item_id_or_error}.")
            print("\nIMPORTANT: OmniFocus data has been changed. Re-export if needed for JSON queries.")

    except Exception as e:
        print(f"An unexpected error occurred during AppleScript execution: {e}")

