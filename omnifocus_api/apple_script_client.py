import subprocess
import shlex
import re
from typing import Optional, List, Tuple
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
    try:
        print(f"Creating task: '{title}' in Inbox")
        result = subprocess.run(["osascript", "-e", base_script], capture_output=True, text=True)
        
        if result.returncode != 0:
            error = result.stderr.strip()
            print(f"AppleScript execution failed: {error}")
            return False, None
        
        task_id = result.stdout.strip()
        if not task_id:
            print("No task ID returned from OmniFocus.")
            return False, None
        
        # Step 2: If we have a project, note, or due date, apply those to the existing task
        if project_name or note or due_date:
            update_script = f'''
            tell application "OmniFocus"
                tell default document
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
                    return id of theTask
                end tell
            end tell
            '''
            
            # Run the update script
            print("Updating task with additional properties...")
            update_result = subprocess.run(["osascript", "-e", update_script], capture_output=True, text=True)
            
            if update_result.returncode != 0:
                error = update_result.stderr.strip()
                print(f"Warning: Failed to update task properties: {error}")
                # Still return success if the initial task was created
        
        print(f"Task '{title}' created successfully in OmniFocus (ID: {task_id}).")
        return True, task_id
    
    except Exception as e:
        print(f"Exception while executing AppleScript: {str(e)}")
        return False, None


def fetch_tasks(project_name: Optional[str] = None) -> List[OmniFocusTask]:
    """
    Fetch tasks from OmniFocus. If project_name is provided, only fetch tasks from that project.
    Returns a list of OmniFocusTask objects.
    """
    filter_clause = ""
    if project_name:
        filter_clause = f'whose name is "{project_name}"'

    as_script = f'''
    tell application "OmniFocus"
        set theDoc to default document
        set output to ""
        
        if "{project_name}" is not "" then
            set theProject to first flattened project of theDoc {filter_clause}
            set theTasks to every task of theProject
        else
            set theTasks to every task of theDoc
        end if

        repeat with t in theTasks
            set taskID to id of t
            set taskName to name of t
            set taskNote to note of t
            set isCompleted to completed of t
            if due date of t is missing value then
                set dd to ""
            else
                set dd to due date of t as string
            end if

            set output to output & taskID & \"||\" & taskName & \"||\" & taskNote & \"||\" & isCompleted & \"||\" & dd & \"\\n\"
        end repeat
        return output
    end tell
    '''

    result = subprocess.run(["osascript", "-e", as_script], capture_output=True, text=True)
    tasks = []
    if result.returncode == 0:
        lines = result.stdout.strip().split("\n")
        for line in lines:
            if not line.strip():
                continue
            parts = line.split("||")
            if len(parts) < 5:
                continue
            task_id, name, note, completed_str, due_date_str = parts
            completed = (completed_str == "true")
            due_date = due_date_str if due_date_str else None
            tasks.append(OmniFocusTask(
                id=task_id, 
                name=name, 
                note=note, 
                completed=completed, 
                due_date=due_date
            ))
    return tasks


def complete_task(task_id: str) -> bool:
    """
    Mark the specified task as completed in OmniFocus.
    Returns True on success, False otherwise.
    """
    as_script = f'''
    tell application "OmniFocus"
        set theDoc to default document
        set theTask to first task of theDoc whose id is "{task_id}"
        set completed of theTask to true
        return (completed of theTask) as string
    end tell
    '''
    result = subprocess.run(["osascript", "-e", as_script], capture_output=True, text=True)
    if result.returncode == 0:
        output = result.stdout.strip().lower()
        return (output == "true")
    else:
        return False


def get_task_by_id(task_id: str) -> Optional[OmniFocusTask]:
    """
    Retrieves a single task by ID.
    Returns an OmniFocusTask or None if not found.
    """
    as_script = f'''
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
            return taskID & \"||\" & taskName & \"||\" & taskNote & \"||\" & isCompleted & \"||\" & dd
        on error
            return ""
        end try
    end tell
    '''
    result = subprocess.run(["osascript", "-e", as_script], capture_output=True, text=True)
    if result.returncode != 0 or not result.stdout.strip():
        return None

    parts = result.stdout.strip().split("||")
    if len(parts) < 5:
        return None

    t_id, name, note, completed_str, due_date_str = parts
    return OmniFocusTask(
        id=t_id,
        name=name,
        note=note,
        completed=(completed_str == "true"),
        due_date=due_date_str if due_date_str else None
    )


def add_tag_to_task(task_id: str, tag_name: str) -> bool:
    """
    Add a tag (context in older versions) to the specified task.
    Returns True on success, False otherwise.
    """
    as_script = f'''
    tell application "OmniFocus"
        set theDoc to default document

        set theTask to first task of theDoc whose id is "{task_id}"
        if theTask is not missing value then
            -- find or create tag
            set existingTag to first flattened tag of theDoc whose name is "{tag_name}"
            if existingTag is missing value then
                set existingTag to make new tag with properties {{name:"{tag_name}"}}
            end if
            set tag of theTask to existingTag
            return "true"
        end if
        return "false"
    end tell
    '''
    result = subprocess.run(["osascript", "-e", as_script], capture_output=True, text=True)
    if result.returncode == 0 and result.stdout.strip() == "true":
        return True
    return False

