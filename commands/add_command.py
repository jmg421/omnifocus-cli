from omnifocus_api import apple_script_client
from ai_integration.utils.format_utils import parse_date_string
import subprocess # For the fallback osascript execution
from typing import Optional, List # Added import for Optional and List
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
    # Order matters: backslash first, then single quote, then double quote
    s = s.replace('\\', '\\\\') # Escape backslashes
    s = s.replace("'", "'\\''") # Escape single quotes for AppleScript (doubling them within a single-quoted string)
                                 # or more robustly: replace ' with '\'' which works inside AS double-quoted strings.
                                 # Let's use the method from the TS example: replace ' with \'
    s = s.replace("'", "\\'")   # Escape single quotes
    s = s.replace('"', '\\"')   # Escape double quotes
    return s

def generate_add_detailed_task_applescript(
    title: str,
    folder_name: Optional[str],
    project_name: Optional[str],
    note: Optional[str],
    due_date_str: Optional[str],
    defer_date_str: Optional[str],
    recurrence_rule_str: Optional[str],
    tags_list: Optional[List[str]]
) -> str:
    script_parts = []
    script_parts.append('tell application "OmniFocus"')
    script_parts.append('    tell default document')
    # taskCreationTarget is defined and used if targeting a specific folder/project for task creation.
    # newTask is the variable for the task once created.

    s_title = escape_applescript_string(title)
    s_note = escape_applescript_string(note) if note else None
    s_folder_name = escape_applescript_string(folder_name) if folder_name else None
    s_project_name = escape_applescript_string(project_name) if project_name else None

    base_task_properties = [f'name:"{s_title}"' ]
    if s_note: # Add note to initial properties if available
        base_task_properties.append(f'note:"{s_note}"' )
    task_properties_str = ", ".join(base_task_properties)

    if s_project_name: # Project is specified
        script_parts.append('        try')
        script_parts.append(f'            set theProject to first flattened project where its name = "{s_project_name}"')
        # Create as an inbox task and then assign to project via 'assigned container'
        script_parts.append(f'            set newTask to make new inbox task with properties {{{task_properties_str}, assigned container:theProject}}')
        script_parts.append('        on error errMsg number errNum')
        script_parts.append(f"            return \"Error: Target project '{s_project_name}' not found or failed to assign task: \" & errMsg & \" (Num: \" & errNum & \")\"")
        script_parts.append('        end try')
    else: # No project specified. Create in true Inbox.
        script_parts.append(f'        set newTask to make new inbox task with properties {{{task_properties_str}}}')

    # Set other properties on newTask (note is already in properties_str if provided)
    # s_note is handled above now
    # if s_note:
    #    script_parts.append(f'        set note of newTask to "{s_note}"')
    if due_date_str:
        script_parts.append(f'        set due date of newTask to date "{due_date_str}"')
    if defer_date_str:
        script_parts.append(f'        set defer date of newTask to date "{defer_date_str}"')
    
    # Add tags if provided
    if tags_list:
        for tag_name in tags_list:
            s_tag_name = escape_applescript_string(tag_name)
            script_parts.append('        try')
            script_parts.append(f'            set theTag to first flattened tag where name = "{s_tag_name}"')
            script_parts.append(f'            tell newTask to add theTag')
            script_parts.append(f'        on error errMsg number errNum')
            # For now, let's report if a tag is not found or fails to add, rather than silently ignoring
            script_parts.append(f"            display dialog (\"Warning: Could not find or add tag '{s_tag_name}'. Error: \" & errMsg & \" (Num: \" & errNum & \")\") with title \"Tag Error\" giving up after 2") # User feedback, corrected syntax
            script_parts.append('        end try')

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
    # DEBUG: Print the title as received by this function
    print(f"DEBUG: handle_add_detailed_task received title: '{title}'")

    folder_name = args.folder_name
    project_name = args.project_name
    note = args.note
    recurrence_rule_str = args.recurrence_rule
    tags_str = args.tags # Get the comma-separated string of tags

    parsed_tags_list: Optional[List[str]] = None
    if tags_str:
        parsed_tags_list = [tag.strip() for tag in tags_str.split(',') if tag.strip()]

    final_due_date_str = None
    if args.due_date:
        dt_obj = None
        if args.due_date.lower() == "next month 1st":
            now = datetime.now()
            dt_obj = (now.replace(day=1) + relativedelta(months=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        elif args.due_date.lower() == "next month 5th":
            now = datetime.now()
            dt_obj = (now.replace(day=1) + relativedelta(months=1)).replace(day=5, hour=0, minute=0, second=0, microsecond=0)
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
        if args.defer_date.lower() == "next month 1st":
            now = datetime.now()
            dt_obj = (now.replace(day=1) + relativedelta(months=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        elif args.defer_date.lower() == "next month 5th":
            now = datetime.now()
            dt_obj = (now.replace(day=1) + relativedelta(months=1)).replace(day=5, hour=0, minute=0, second=0, microsecond=0)
        else:
            parsed_val = parse_date_string(args.defer_date)
            if isinstance(parsed_val, datetime):
                dt_obj = parsed_val
            elif isinstance(parsed_val, str):
                print(f"Warning: Defer date string '{args.defer_date}' could not be parsed into a datetime object. Defer date may not be set correctly.")
                final_defer_date_str = parsed_val

        if dt_obj:
            final_defer_date_str = dt_obj.strftime("%B %d, %Y %H:%M:%S")

    if project_name and folder_name: # This check is actually in ofcli.py, effectively making one of them None here
        print("Error: Please specify either a project or a folder, not both.") # Should not be reached if CLI validation is correct
        return

    # Informational message about folder_name usage if applicable
    if folder_name and not project_name:
        print(f"Info: --folder-name '{folder_name}' was provided without --project-name. Task will be created in the Inbox. OmniFocus tasks live in projects or the Inbox.")

    applescript_command = generate_add_detailed_task_applescript(
        title, 
        None, # folder_name is not used for targeting project/inbox directly in this new model
        project_name, 
        note, 
        final_due_date_str, 
        final_defer_date_str, 
        recurrence_rule_str,
        parsed_tags_list # Pass the parsed list of tags
    )

    print("\nGenerated AppleScript for add-task (for review):")
    print("------------------------------------")
    print(applescript_command)
    print("------------------------------------\n")

    execute_omnifocus_applescript = None
    try:
        from omnifocus_api.apple_script_client import execute_omnifocus_applescript
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
        from omnifocus_api.apple_script_client import execute_omnifocus_applescript
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

