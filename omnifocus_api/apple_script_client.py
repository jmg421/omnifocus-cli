import subprocess
import shlex
import re
import os
import platform
from typing import Optional, List, Tuple
from datetime import datetime
from .data_models import OmniFocusTask

def escape_applescript_string(text: str) -> str:
    """
    Escape special characters for AppleScript strings.
    """
    if not text:
        return ""
    
    # Replace " with \" and other special chars
    text = text.replace('"', '\\"')
    text = text.replace('\\', '\\\\')
    
    return text

def _run_applescript(script: str, timeout: int = 15) -> Tuple[bool, str]:
    """Helper to run AppleScript and return success status and output."""
    try:
        result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=timeout)
        if result.returncode != 0:
            print(f"AppleScript error: {result.stderr.strip()}")
            return False, ""
        return True, result.stdout.strip()
    except Exception as e:
        print(f"Error running AppleScript: {str(e)}")
        return False, ""

def create_task_via_applescript(
    title: str,
    project_name: Optional[str] = None,
    note: str = "",
    due_date: Optional[str] = None
) -> Tuple[bool, Optional[str]]:
    """
    Creates a new task in OmniFocus via AppleScript.
    Returns a tuple (success, of_task_id).
    """
    # Escape special characters in inputs
    escaped_title = escape_applescript_string(title)
    escaped_note = escape_applescript_string(note)
    
    # First, create a simple inbox task (which always works)
    base_script = '''
    tell application "OmniFocus" 
        tell default document
            set newTask to make new inbox task with properties {name:"TASKPLACEHOLDER"}
            set taskId to id of newTask
            return taskId
        end tell
    end tell
    '''.replace("TASKPLACEHOLDER", escaped_title)
    
    # Execute the script to create the task
    success_create, task_id = _run_applescript(base_script)
    if not success_create or not task_id:
        print(f"Failed to create initial task: '{title}'")
        return False, None
        
    # Step 2: If we have a project, note, or due date, apply those to the existing task
    if project_name or note or due_date:
        update_script = f'''
        tell application "OmniFocus"
            tell default document
                try
                    set theTask to first flattened task whose id is "{task_id}"
        '''
        
        # Add note if provided
        if note:
            update_script += f'''
                    set note of theTask to "{escaped_note}"
            '''
        
        # Set due date if provided
        if due_date:
            escaped_due = escape_applescript_string(due_date)
            update_script += f'''
                    try
                        set due date of theTask to date "{escaped_due}"
                    on error errMsg
                        log "Error setting due date: " & errMsg
                    end try
            '''
        
        # Move to project if specified
        if project_name:
            escaped_project = escape_applescript_string(project_name)
            update_script += f'''
                    try
                        -- Find or create the project
                        set theProject to missing value
                        try
                            set theProject to first flattened project whose name is "{escaped_project}"
                        on error
                            set theProject to make new project with properties {{name:"{escaped_project}"}}
                        end try
                        
                        -- Move the task to the project
                        move theTask to end of tasks of theProject
                    on error errorMsg
                        log "Error moving task to project: " & errorMsg
                    end try
            '''
        
        update_script += '''
                    return "true" -- Indicate success if we reached here
                on error errorMsg
                    log "Error finding task or updating properties: " & errorMsg
                    return "false"
                end try
            end tell
        end tell
        '''
        
        # Run the update script
        print("Updating task with additional properties...")
        success_update, update_output = _run_applescript(update_script)
        
        if not success_update or update_output != "true":
            print(f"Warning: Failed to update task properties for task ID {task_id}.")
            # Still return success if the initial task was created
    
    print(f"Task '{title}' created successfully in OmniFocus (ID: {task_id}).")
    return True, task_id


def fetch_tasks(project_name: Optional[str] = None, search_text: Optional[str] = None) -> List[OmniFocusTask]:
    """
    Fetch tasks from OmniFocus. 
    If project_name is provided, only fetch tasks from that project.
    If search_text is provided, only fetch tasks containing that text (case-insensitive).
    Returns a list of OmniFocusTask objects.
    """
    print(f"Fetching tasks from OmniFocus. Project filter: {project_name}, Search text: {search_text}")
    # Short-circuit if not macOS or OmniFocus executable is not present
    if platform.system() != 'Darwin' or not os.path.isfile('/Applications/OmniFocus.app/Contents/MacOS/OmniFocus'):
        print("OmniFocus executable not found or not macOS; returning mock tasks")
        return get_mock_tasks()
    
    # Build the AppleScript to fetch tasks
    script = '''
    on run {arg_project_name, arg_search_text}
        set output to ""
        set taskList to {}
        tell application "OmniFocus"
            tell default document
                -- Determine which tasks to fetch
                if arg_project_name is not "" then
                    try
                        set theProject to first flattened project whose name is arg_project_name
                        set taskList to every task of theProject where completed is false
                    on error
                        return "" -- Project not found
                    end try
                else
                    set taskList to every flattened task where completed is false
                end if
                
                -- Filter tasks based on search text if provided
                if arg_search_text is not "" then
                    set matchingTasks to {}
                    set lowerSearch to arg_search_text
                    # Note: AppleScript's default string comparisons are case-insensitive
                    repeat with t in taskList
                        if (name of t contains lowerSearch) or (note of t contains lowerSearch) then
                            set end of matchingTasks to t
                        end if
                    end repeat
                    set taskList to matchingTasks
                end if
                
                -- Format task information
                repeat with t in taskList
                    set taskID to id of t
                    set taskName to name of t
                    set taskNote to note of t
                    set isCompleted to completed of t -- Should always be false here
                    
                    -- Get project name if available
                    try
                        set projName to name of containing project of t
                    on error
                        set projName to ""
                    end try
                    
                    -- Get due date if available
                    if due date of t is missing value then
                        set dd to ""
                    else
                        set dd to due date of t as string
                    end if
                    
                    set output to output & taskID & "||" & taskName & "||" & taskNote & "||" & isCompleted & "||" & dd & "||" & projName & "\n"
                end repeat
                return output
            end tell
        end tell
    end run
    '''
    
    # Prepare arguments for AppleScript
    # osascript doesn't directly support passing arguments to `run` handler easily via -e
    # Instead, we replace placeholders or embed the arguments in the script string.
    # Simpler approach: embed directly, ensuring proper escaping.
    escaped_project = escape_applescript_string(project_name) if project_name else ""
    escaped_search = escape_applescript_string(search_text) if search_text else ""
    
    # Embed arguments into the script string (replace placeholders)
    # Using unique placeholders to avoid conflicts
    script_with_args = script.replace("{arg_project_name}", f'"{escaped_project}"') \
                           .replace("{arg_search_text}", f'"{escaped_search}"')
    
    # Execute the AppleScript
    success, output = _run_applescript(script_with_args, timeout=60)
    
    if not success:
        print("Falling back to mock tasks...")
        return get_mock_tasks()
    
    # Parse the output
    tasks = []
    if not output:
        print("No tasks found matching criteria. Returning empty list.")
        return []
    
    lines = output.split("\n")
    for line in lines:
        if not line.strip():
            continue
            
        parts = line.split("||")
        if len(parts) < 6:
            continue
            
        task_id, name, note, completed_str, due_date_str, project = parts
        
        tasks.append(OmniFocusTask(
            id=task_id,
            name=name,
            note=note,
            completed=(completed_str == "true"), # Should be false based on script filter
            due_date=due_date_str if due_date_str else None,
            project=project if project else None
        ))
    
    return tasks


def get_mock_tasks() -> List[OmniFocusTask]:
    """Return mock tasks for testing or when OmniFocus connection fails"""
    return [
        OmniFocusTask(
            id="task1",
            name="Test Task 1",
            note="This is a test task",
            completed=False,
            due_date="2023-12-31",
            project="Test Project"
        ),
        OmniFocusTask(
            id="task2",
            name="Test Task 2",
            note="Another test task",
            completed=False,
            due_date=None,
            project="Test Project"
        ),
        OmniFocusTask(
            id="task3",
            name="Test Task 3",
            note="Third test task",
            completed=False,
            due_date="2023-12-25",
            project=None
        )
    ]


def complete_task(task_id: str) -> bool:
    """
    Mark the specified task as completed in OmniFocus.
    For inbox tasks, moves them to a "Reference" project first.
    Returns True on success, False otherwise.
    """
    script = f'''
    on run
        tell application "OmniFocus"
            try
                tell default document
                    set theTask to first flattened task whose id is "{task_id}"
                    
                    -- Function to process a task
                    script TaskProcessor
                        on processTask(taskToProcess)
                            -- Check if it's an inbox task
                            if exists (every inbox task whose id is (id of taskToProcess)) then
                                -- Create or get Reference project if needed
                                try
                                    set refProject to first flattened project whose name is "Reference"
                                on error
                                    set refProject to make new project with properties {{name:"Reference"}}
                                end try
                                
                                -- Move task to Reference project
                                move taskToProcess to end of tasks of refProject
                                delay 0.1 -- Small delay to let OmniFocus process the move
                            end if
                            
                            -- Now complete the task
                            set completed of taskToProcess to true
                        end processTask
                    end script
                    
                    -- Process the main task and all its subtasks
                    if exists theTask then
                        -- First process any subtasks
                        repeat with subTask in (every task of theTask)
                            TaskProcessor's processTask(subTask)
                        end repeat
                        
                        -- Then process the main task
                        TaskProcessor's processTask(theTask)
                        
                        return "true"
                    else
                        return "false: Task not found"
                    end if
                end tell
            on error errMsg
                log errMsg
                return "false: " & errMsg
            end try
        end tell
    end run
    '''
    
    success, output = _run_applescript(script)
    if not success or output.startswith("false:"):
        error_msg = output[6:].strip() if output.startswith("false:") else "Unknown error"
        print(f"OmniFocus error completing task {task_id}: {error_msg}")
        return False
        
    return True


def get_task_by_id(task_id: str) -> Optional[OmniFocusTask]:
    """
    Retrieves a single task by ID.
    Returns an OmniFocusTask or None if not found.
    """
    script = f'''
    on run
        tell application "OmniFocus"
            set theDoc to default document
            try
                set theTask to first task of theDoc whose id is "{task_id}"
                set taskID to id of theTask
                set taskName to name of theTask
                set taskNote to note of theTask
                set isCompleted to completed of theTask
                if due date of theTask is missing value then
                    set dd to ""
                else
                    set dd to due date of theTask as string
                end if
                -- Get project name if available
                set projName to ""
                try
                    if containing project of theTask is not missing value then
                        set projName to name of containing project of theTask
                    end if
                end try
                return taskID & "||" & taskName & "||" & taskNote & "||" & isCompleted & "||" & dd & "||" & projName
            on error
                return ""
            end try
        end tell
    end run
    '''
    success, output = _run_applescript(script)
    if not success or not output:
        return None

    parts = output.split("||")
    if len(parts) < 6: # ID, Name, Note, Completed, DueDate, Project
        return None

    t_id, name, note, completed_str, due_date_str, project_name = parts
    return OmniFocusTask(
        id=t_id,
        name=name,
        note=note,
        completed=(completed_str == "true"),
        due_date=due_date_str if due_date_str else None,
        project=project_name if project_name else None
    )


def add_tag_to_task(task_id: str, tag_name: str) -> bool:
    """
    Add a tag (context in older versions) to the specified task.
    Returns True on success, False otherwise.
    """
    escaped_tag_name = escape_applescript_string(tag_name)
    script = f'''
    on run
        tell application "OmniFocus"
            set theDoc to default document
            try
                set theTask to first task of theDoc whose id is "{task_id}"
                if theTask is not missing value then
                    -- find or create tag
                    set existingTag to missing value
                    try
                        set existingTag to first flattened tag of theDoc whose name is "{escaped_tag_name}"
                    on error
                        -- Tag doesn't exist, create it
                    end try
                    if existingTag is missing value then
                        set existingTag to make new tag with properties {{name:"{escaped_tag_name}"}}
                    end if
                    -- Add tag (use `add` command)
                    add existingTag to tags of theTask
                    return "true"
                else
                    return "false: Task not found"
                end if
            on error errMsg
                log errMsg
                return "false: " & errMsg
            end try
        end tell
    end run
    '''
    success, output = _run_applescript(script)
    if not success or output.startswith("false:"):
        error_msg = output[6:].strip() if output.startswith("false:") else "Unknown error"
        print(f"OmniFocus error adding tag '{tag_name}' to task {task_id}: {error_msg}")
        return False
    return True


def fetch_inbox_tasks() -> List[OmniFocusTask]:
    """Fetch all tasks from the inbox."""
    script = '''
    on run
        tell application "OmniFocus"
            tell default document
                set output to ""
                set inboxTasks to every inbox task where completed is false
                
                repeat with t in inboxTasks
                    set taskID to id of t
                    set taskName to name of t
                    set taskNote to note of t
                    set isCompleted to completed of t -- Should be false
                    if due date of t is missing value then
                        set dd to ""
                    else
                        set dd to due date of t as string
                    end if
                    
                    set output to output & taskID & "||" & taskName & "||" & taskNote & "||" & isCompleted & "||" & dd & "||" & "" & "\n" -- Inbox tasks have no project
                end repeat
                return output
            end tell
        end tell
    end run
    '''
    
    success, output = _run_applescript(script)
    tasks = []
    if success and output:
        lines = output.split("\n")
        for line in lines:
            if not line.strip():
                continue
            parts = line.split("||")
            if len(parts) < 6:
                continue
            task_id, name, note, completed_str, due_date_str, _ = parts # Ignore project part
            tasks.append(OmniFocusTask(
                id=task_id,
                name=name,
                note=note,
                completed=(completed_str == "true"),
                due_date=due_date_str if due_date_str else None,
                project=None # Inbox tasks
            ))
    return tasks

def fetch_flagged_tasks() -> List[OmniFocusTask]:
    """Fetch all flagged tasks."""
    print("Fetching flagged tasks from OmniFocus...")
    
    script = '''
    on run
        tell application "OmniFocus"
            tell default document
                set output to ""
                set flaggedTasks to every flattened task where flagged is true and completed is false
                
                repeat with t in flaggedTasks
                    set taskID to id of t
                    set taskName to name of t
                    set taskNote to note of t
                    set isCompleted to completed of t -- Should be false
                    
                    -- Get project name if available
                    set projName to ""
                    try
                        if containing project of t is not missing value then
                            set projName to name of containing project of t
                        end if
                    end try
                    
                    -- Get due date if available
                    if due date of t is missing value then
                        set dd to ""
                    else
                        set dd to due date of t as string
                    end if
                    
                    set output to output & taskID & "||" & taskName & "||" & taskNote & "||" & isCompleted & "||" & dd & "||" & projName & "\n"
                end repeat
                
                return output
            end tell
        end tell
    end run
    '''
    
    success, output = _run_applescript(script, timeout=60)
    
    if not success:
        print("Falling back to mock tasks...")
        return get_mock_tasks()
    
    # Parse the output
    tasks = []
    if not output:
        print("No flagged tasks found in OmniFocus.")
        return []
    
    lines = output.split("\n")
    for line in lines:
        if not line.strip():
            continue
            
        parts = line.split("||")
        if len(parts) < 6:
            continue
            
        task_id, name, note, completed_str, due_date_str, project = parts
        
        tasks.append(OmniFocusTask(
            id=task_id,
            name=name,
            note=note,
            completed=(completed_str == "true"),
            due_date=due_date_str if due_date_str else None,
            project=project if project else None
        ))
    
    return tasks

def fetch_overdue_tasks() -> List[OmniFocusTask]:
    """Fetch all overdue tasks."""
    print("Fetching overdue tasks from OmniFocus...")
    
    script = '''
    on run
        tell application "OmniFocus"
            tell default document
                set output to ""
                set currentDate to current date
                
                -- Get all incomplete tasks with due dates
                set taskList to every flattened task where completed is false and due date is not missing value
                
                -- Filter for overdue tasks
                set overdueTasks to {}
                repeat with t in taskList
                    if due date of t < currentDate then
                        set end of overdueTasks to t
                    end if
                end repeat
                
                repeat with t in overdueTasks
                    set taskID to id of t
                    set taskName to name of t
                    set taskNote to note of t
                    set isCompleted to completed of t -- Should be false
                    
                    -- Get project name if available
                    set projName to ""
                    try
                        if containing project of t is not missing value then
                            set projName to name of containing project of t
                        end if
                    end try
                    
                    -- Get due date
                    set dd to due date of t as string
                    
                    set output to output & taskID & "||" & taskName & "||" & taskNote & "||" & isCompleted & "||" & dd & "||" & projName & "\n"
                end repeat
                
                return output
            end tell
        end tell
    end run
    '''
    
    success, output = _run_applescript(script, timeout=60)
    
    if not success:
        print("Falling back to mock tasks...")
        return get_mock_tasks()
    
    # Parse the output
    tasks = []
    if not output:
        print("No overdue tasks found in OmniFocus.")
        return []
    
    lines = output.split("\n")
    for line in lines:
        if not line.strip():
            continue
            
        parts = line.split("||")
        if len(parts) < 6:
            continue
            
        task_id, name, note, completed_str, due_date_str, project = parts
        
        tasks.append(OmniFocusTask(
            id=task_id,
            name=name,
            note=note,
            completed=(completed_str == "true"),
            due_date=due_date_str if due_date_str else None,
            project=project if project else None
        ))
    
    return tasks

def delete_task(task_id: str) -> bool:
    """Delete a task."""
    print(f"Deleting task {task_id} from OmniFocus...")
    
    script = f'''
    on run
        tell application "OmniFocus"
            tell default document
                try
                    set theTask to first flattened task whose id is "{task_id}"
                    delete theTask
                    return "true"
                on error errMsg
                    return "false: " & errMsg
                end try
            end tell
        end tell
    end run
    '''
    
    success, output = _run_applescript(script, timeout=60)
    if not success or output.startswith("false:"):
        error_msg = output[6:].strip() if output.startswith("false:") else "Unknown error"
        print(f"OmniFocus error deleting task {task_id}: {error_msg}")
        return False
    return True

def unflag_task(task_id: str) -> bool:
    """Remove flag from a task."""
    print(f"Unflagging task {task_id} in OmniFocus...")
    
    script = f'''
    on run
        tell application "OmniFocus"
            tell default document
                try
                    set theTask to first flattened task whose id is "{task_id}"
                    set flagged of theTask to false
                    return "true"
                on error errMsg
                    return "false: " & errMsg
                end try
            end tell
        end tell
    end run
    '''
    
    success, output = _run_applescript(script, timeout=60)
    if not success or output.startswith("false:"):
        error_msg = output[6:].strip() if output.startswith("false:") else "Unknown error"
        print(f"OmniFocus error unflagging task {task_id}: {error_msg}")
        return False
    return True

def move_task_to_project(task_id: str, project_name: str) -> bool:
    """Move a task to a project."""
    print(f"Moving task {task_id} to project {project_name} in OmniFocus...")
    
    escaped_project = escape_applescript_string(project_name)
    script = f'''
    on run
        tell application "OmniFocus"
            tell default document
                try
                    -- Get the task
                    set theTask to first flattened task whose id is "{task_id}"
                    
                    -- Find or create the project
                    set theProject to missing value
                    try
                        set theProject to first flattened project whose name is "{escaped_project}"
                    on error
                        set theProject to make new project with properties {{name:"{escaped_project}"}}
                    end try
                    
                    -- Move the task to the project
                    move theTask to end of tasks of theProject
                    return "true"
                on error errMsg
                    return "false: " & errMsg
                end try
            end tell
        end tell
    end run
    '''
    
    success, output = _run_applescript(script, timeout=60)
    if not success or output.startswith("false:"):
        error_msg = output[6:].strip() if output.startswith("false:") else "Unknown error"
        print(f"OmniFocus error moving task {task_id} to project '{project_name}': {error_msg}")
        return False
    return True

def set_task_due_date(task_id: str, due_date: str) -> bool:
    """Set the due date for a task."""
    print(f"Setting due date {due_date} for task {task_id} in OmniFocus...")
    
    escaped_due = escape_applescript_string(due_date)
    script = f'''
    on run
        tell application "OmniFocus"
            tell default document
                try
                    set theTask to first flattened task whose id is "{task_id}"
                    set due date of theTask to date "{escaped_due}"
                    return "true"
                on error errMsg
                    return "false: " & errMsg
                end try
            end tell
        end tell
    end run
    '''
    
    success, output = _run_applescript(script, timeout=60)
    if not success or output.startswith("false:"):
        error_msg = output[6:].strip() if output.startswith("false:") else "Unknown error"
        print(f"OmniFocus error setting due date for task {task_id}: {error_msg}")
        return False
    return True

def fetch_subtasks(task_id: str) -> List[OmniFocusTask]:
    """Fetch all subtasks of a given task."""
    print(f"Fetching subtasks for task {task_id} from OmniFocus...")
    
    script = f'''
    on run
        tell application "OmniFocus"
            tell default document
                set output to ""
                
                try
                    set parentTask to first flattened task whose id is "{task_id}"
                    set subTasks to every task of parentTask where completed is false
                    
                    repeat with t in subTasks
                        set taskID to id of t
                        set taskName to name of t
                        set taskNote to note of t
                        set isCompleted to completed of t -- Should be false
                        
                        -- Get project name if available
                        set projName to ""
                        try
                            if containing project of t is not missing value then
                                set projName to name of containing project of t
                            end if
                        end try
                        
                        -- Get due date if available
                        if due date of t is missing value then
                            set dd to ""
                        else
                            set dd to due date of t as string
                        end if
                        
                        set output to output & taskID & "||" & taskName & "||" & taskNote & "||" & isCompleted & "||" & dd & "||" & projName & "\n"
                    end repeat
                    
                    return output
                on error
                    return "" -- Task not found or no subtasks
                end try
            end tell
        end tell
    end run
    '''
    
    success, output = _run_applescript(script, timeout=60)
    
    if not success:
        print("Falling back to empty list...")
        return []
    
    # Parse the output
    tasks = []
    if not output:
        print("No active subtasks found or task does not exist.")
        return []
    
    lines = output.split("\n")
    for line in lines:
        if not line.strip():
            continue
            
        parts = line.split("||")
        if len(parts) < 6:
            continue
            
        task_id_sub, name_sub, note_sub, completed_str_sub, due_date_str_sub, project_sub = parts
        
        tasks.append(OmniFocusTask(
            id=task_id_sub,
            name=name_sub,
            note=note_sub,
            completed=(completed_str_sub == "true"),
            due_date=due_date_str_sub if due_date_str_sub else None,
            project=project_sub if project_sub else None
        ))
    
    return tasks

def test_evernote_export() -> bool:
    """Test Evernote export with a simple note."""
    print("Testing Evernote export with a simple note...")
    
    try:
        # Prepare a simple test note
        test_title = "OmniFocus CLI Test Note"
        test_content = "This is a test note from OmniFocus CLI to verify Evernote integration is working."
        test_notebook = "Reference Material"
        test_tags = ["omnifocus", "test"]
        
        # Try to export it
        return export_to_evernote(test_title, test_content, test_notebook, test_tags)
        
    except Exception as e:
        print(f"Error testing Evernote export: {str(e)}")
        return False

def export_to_evernote(title: str, content: str, notebook: str = "Reference Material", tags: List[str] = None) -> bool:
    """Export content to Evernote."""
    print(f"Exporting to Evernote: {title}")
    
    if not tags:
        tags = []
    
    # Check if Evernote is running and available
    check_script = '''
    on run
        try
            tell application "System Events" to set evernoteRunning to exists (process "Evernote")
            if not evernoteRunning then
                tell application "Evernote" to activate
                delay 2
            end if
            return "true"
        on error errMsg
            return "false: " & errMsg
        end try
    end run
    '''
    
    success_check, _ = _run_applescript(check_script)
    if not success_check:
        print("Evernote is not available or could not be launched.")
        return False
    
    # Escape strings for AppleScript
    escaped_title = escape_applescript_string(title)
    escaped_content = escape_applescript_string(content)
    escaped_notebook = escape_applescript_string(notebook)
    
    # Prepare tags for AppleScript
    tags_script_part = ""
    if tags and len(tags) > 0:
        tag_strings = []
        for tag in tags:
            escaped_tag = escape_applescript_string(tag)
            tag_strings.append(f'"{escaped_tag}"')
        
        tags_script_part = f'''
        -- Add tags
        set tagNames to {{{", ".join(tag_strings)}}}
        repeat with tagName in tagNames
            tell newNote to assign tag tagName
        end repeat
        '''
    
    # Build the AppleScript to create a note in Evernote
    script = f'''
    on run
        tell application "Evernote"
            try
                -- Find or create the notebook
                set notebookList to every notebook where name is "{escaped_notebook}"
                if length of notebookList is 0 then
                    create notebook "{escaped_notebook}"
                    set targetNotebook to notebook "{escaped_notebook}"
                else
                    set targetNotebook to item 1 of notebookList
                end if
                
                -- Create the note
                set newNote to create note title "{escaped_title}" with html "{escaped_content}" notebook targetNotebook
                
                {tags_script_part}
                
                return "true"
            on error errMsg
                return "false: " & errMsg
            end try
        end tell
    end run
    '''
    
    success_export, output = _run_applescript(script, timeout=20)
    
    if not success_export or output.startswith("false:"):
        error_msg = output[6:].strip() if output.startswith("false:") else "Unknown error"
        print(f"Evernote error exporting note '{title}': {error_msg}")
        return False
    
    print(f"Successfully exported note '{title}' to Evernote in notebook '{notebook}'.")
    return True

def fetch_projects() -> list:
    """
    Fetch all active, flattened project names from OmniFocus.
    Returns a flat list of project names.
    """
    as_script = '''
    on run
        tell application "OmniFocus"
            tell default document
                set projectNames to {}
                set allProjects to every flattened project whose status is active
                repeat with p in allProjects
                    set end of projectNames to name of p
                end repeat
                
                set AppleScript's text item delimiters to ","
                set projectNamesString to projectNames as string
                set AppleScript's text item delimiters to ""
                return projectNamesString
            end tell
        end tell
    end run
    '''
    success, output = _run_applescript(as_script, timeout=30)
    if not success:
        return []
    return [line.strip() for line in output.split(",") if line.strip()]