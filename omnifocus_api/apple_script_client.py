import subprocess
import shlex
import re
import os
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


def fetch_tasks(project_name: Optional[str] = None, search_text: Optional[str] = None) -> List[OmniFocusTask]:
    """
    Fetch tasks from OmniFocus. 
    If project_name is provided, only fetch tasks from that project.
    If search_text is provided, only fetch tasks containing that text (case-insensitive).
    Returns a list of OmniFocusTask objects.
    """
    print(f"Fetching tasks from OmniFocus. Project filter: {project_name}, Search text: {search_text}")
    
    try:
        # Build the AppleScript to fetch tasks
        as_script = '''
        tell application "OmniFocus"
            tell default document
                set output to ""
                set allTasks to {}
                
                -- Determine which tasks to fetch
        '''
        
        if project_name:
            # Escape the project name for AppleScript
            escaped_project = escape_applescript_string(project_name)
            as_script += f'''
                try
                    set theProject to first flattened project whose name is "{escaped_project}"
                    set allTasks to every task of theProject
                on error
                    -- Project not found, return empty list
                    return ""
                end try
            '''
        else:
            as_script += '''
                -- Get all available tasks
                set allTasks to every flattened task
            '''
        
        as_script += '''
                -- Filter tasks based on search text if provided
        '''
        
        if search_text:
            escaped_search = escape_applescript_string(search_text.lower())
            as_script += f'''
                set matchingTasks to {{}}
                repeat with t in allTasks
                    set taskName to name of t
                    set taskNote to note of t
                    if taskName contains "{escaped_search}" or taskNote contains "{escaped_search}" then
                        set end of matchingTasks to t
                    end if
                end repeat
                set allTasks to matchingTasks
            '''
        
        as_script += '''
                -- Format task information
                repeat with t in allTasks
                    if completed of t is false then
                        set taskID to id of t
                        set taskName to name of t
                        set taskNote to note of t
                        set isCompleted to completed of t
                        
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
                        
                        set output to output & taskID & "||" & taskName & "||" & taskNote & "||" & isCompleted & "||" & dd & "||" & projName & "\\n"
                    end if
                end repeat
                
                return output
            end tell
        end tell
        '''
        
        # Execute the AppleScript
        result = subprocess.run(["osascript", "-e", as_script], capture_output=True, text=True, timeout=10)
        
        if result.returncode != 0:
            print(f"AppleScript error: {result.stderr.strip()}")
            print("Falling back to mock tasks...")
            return get_mock_tasks()
        
        # Parse the output
        tasks = []
        output = result.stdout.strip()
        
        if not output:
            print("No tasks found in OmniFocus. Returning empty list.")
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
    
    except Exception as e:
        print(f"Error fetching tasks from OmniFocus: {str(e)}")
        print("Falling back to mock tasks...")
        return get_mock_tasks()


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
    as_script = f'''
    tell application "OmniFocus"
        try
            tell default document
                set theTask to first flattened task whose id is "{task_id}"
                
                -- Function to process a task
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
                
                -- Process the main task and all its subtasks
                if exists theTask then
                    -- First process any subtasks
                    repeat with subTask in (every task of theTask)
                        my processTask(subTask)
                    end repeat
                    
                    -- Then process the main task
                    my processTask(theTask)
                    
                    return "true"
                end if
                
                return "false: Task not found"
            end tell
        on error errMsg
            log errMsg
            return "false: " & errMsg
        end try
    end tell
    '''
    
    try:
        result = subprocess.run(["osascript", "-e", as_script], capture_output=True, text=True)
        if result.returncode != 0:
            print(f"AppleScript error: {result.stderr.strip()}")
            return False
            
        output = result.stdout.strip()
        if output.startswith("false:"):
            print(f"OmniFocus error: {output[6:]}")  # Skip "false: " prefix
            return False
            
        return output.lower() == "true"
    except Exception as e:
        print(f"Python error while completing task: {str(e)}")
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


def fetch_inbox_tasks() -> List[OmniFocusTask]:
    """Fetch all tasks from the inbox."""
    as_script = '''
    tell application "OmniFocus"
        tell default document
            set output to ""
            set inboxTasks to every inbox task
            
            repeat with t in inboxTasks
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
            tasks.append(OmniFocusTask(
                id=task_id,
                name=name,
                note=note,
                completed=(completed_str == "true"),
                due_date=due_date_str if due_date_str else None
            ))
    return tasks

def fetch_flagged_tasks() -> List[OmniFocusTask]:
    """Fetch all flagged tasks."""
    print("Fetching flagged tasks from OmniFocus...")
    
    try:
        as_script = '''
        tell application "OmniFocus"
            tell default document
                set output to ""
                set flaggedTasks to every flattened task where flagged is true and completed is false
                
                repeat with t in flaggedTasks
                    set taskID to id of t
                    set taskName to name of t
                    set taskNote to note of t
                    set isCompleted to completed of t
                    
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
                    
                    set output to output & taskID & "||" & taskName & "||" & taskNote & "||" & isCompleted & "||" & dd & "||" & projName & "\\n"
                end repeat
                
                return output
            end tell
        end tell
        '''
        
        result = subprocess.run(["osascript", "-e", as_script], capture_output=True, text=True, timeout=10)
        
        if result.returncode != 0:
            print(f"AppleScript error: {result.stderr.strip()}")
            print("Falling back to mock tasks...")
            return get_mock_tasks()
        
        # Parse the output
        tasks = []
        output = result.stdout.strip()
        
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
    
    except Exception as e:
        print(f"Error fetching flagged tasks from OmniFocus: {str(e)}")
        print("Falling back to mock tasks...")
        return get_mock_tasks()

def fetch_overdue_tasks() -> List[OmniFocusTask]:
    """Fetch all overdue tasks."""
    print("Fetching overdue tasks from OmniFocus...")
    
    try:
        # Current date as string (AppleScript format)
        current_date = datetime.now().strftime("%Y-%m-%d")
        
        as_script = f'''
        tell application "OmniFocus"
            tell default document
                set output to ""
                set currentDate to current date
                
                -- Get all incomplete tasks with due dates
                set allTasks to every flattened task where completed is false and due date is not missing value
                
                -- Filter for overdue tasks
                set overdueTasks to {{}}
                repeat with t in allTasks
                    if due date of t < currentDate then
                        set end of overdueTasks to t
                    end if
                end repeat
                
                repeat with t in overdueTasks
                    set taskID to id of t
                    set taskName to name of t
                    set taskNote to note of t
                    set isCompleted to completed of t
                    
                    -- Get project name if available
                    try
                        set projName to name of containing project of t
                    on error
                        set projName to ""
                    end try
                    
                    -- Get due date
                    set dd to due date of t as string
                    
                    set output to output & taskID & "||" & taskName & "||" & taskNote & "||" & isCompleted & "||" & dd & "||" & projName & "\\n"
                end repeat
                
                return output
            end tell
        end tell
        '''
        
        result = subprocess.run(["osascript", "-e", as_script], capture_output=True, text=True, timeout=10)
        
        if result.returncode != 0:
            print(f"AppleScript error: {result.stderr.strip()}")
            print("Falling back to mock tasks...")
            return get_mock_tasks()
        
        # Parse the output
        tasks = []
        output = result.stdout.strip()
        
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
    
    except Exception as e:
        print(f"Error fetching overdue tasks from OmniFocus: {str(e)}")
        print("Falling back to mock tasks...")
        return get_mock_tasks()

def delete_task(task_id: str) -> bool:
    """Delete a task."""
    print(f"Deleting task {task_id} from OmniFocus...")
    
    try:
        as_script = f'''
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
        '''
        
        result = subprocess.run(["osascript", "-e", as_script], capture_output=True, text=True, timeout=10)
        
        if result.returncode != 0:
            print(f"AppleScript error: {result.stderr.strip()}")
            return False
        
        output = result.stdout.strip()
        if output.startswith("false:"):
            print(f"OmniFocus error: {output[6:]}")
            return False
        
        return output.lower() == "true"
        
    except Exception as e:
        print(f"Error deleting task: {str(e)}")
        return False

def unflag_task(task_id: str) -> bool:
    """Remove flag from a task."""
    print(f"Unflagging task {task_id} in OmniFocus...")
    
    try:
        as_script = f'''
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
        '''
        
        result = subprocess.run(["osascript", "-e", as_script], capture_output=True, text=True, timeout=10)
        
        if result.returncode != 0:
            print(f"AppleScript error: {result.stderr.strip()}")
            return False
        
        output = result.stdout.strip()
        if output.startswith("false:"):
            print(f"OmniFocus error: {output[6:]}")
            return False
        
        return output.lower() == "true"
        
    except Exception as e:
        print(f"Error unflagging task: {str(e)}")
        return False

def move_task_to_project(task_id: str, project_name: str) -> bool:
    """Move a task to a project."""
    print(f"Moving task {task_id} to project {project_name} in OmniFocus...")
    
    try:
        # Escape the project name for AppleScript
        escaped_project = escape_applescript_string(project_name)
        
        as_script = f'''
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
        '''
        
        result = subprocess.run(["osascript", "-e", as_script], capture_output=True, text=True, timeout=10)
        
        if result.returncode != 0:
            print(f"AppleScript error: {result.stderr.strip()}")
            return False
        
        output = result.stdout.strip()
        if output.startswith("false:"):
            print(f"OmniFocus error: {output[6:]}")
            return False
        
        return output.lower() == "true"
        
    except Exception as e:
        print(f"Error moving task to project: {str(e)}")
        return False

def set_task_due_date(task_id: str, due_date: str) -> bool:
    """Set the due date for a task."""
    print(f"Setting due date {due_date} for task {task_id} in OmniFocus...")
    
    try:
        # Escape the due date string for AppleScript
        escaped_due = escape_applescript_string(due_date)
        
        as_script = f'''
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
        '''
        
        result = subprocess.run(["osascript", "-e", as_script], capture_output=True, text=True, timeout=10)
        
        if result.returncode != 0:
            print(f"AppleScript error: {result.stderr.strip()}")
            return False
        
        output = result.stdout.strip()
        if output.startswith("false:"):
            print(f"OmniFocus error: {output[6:]}")
            return False
        
        return output.lower() == "true"
        
    except Exception as e:
        print(f"Error setting task due date: {str(e)}")
        return False

def fetch_subtasks(task_id: str) -> List[OmniFocusTask]:
    """Fetch all subtasks of a given task."""
    print(f"Fetching subtasks for task {task_id} from OmniFocus...")
    
    try:
        as_script = f'''
        tell application "OmniFocus"
            tell default document
                set output to ""
                
                try
                    set parentTask to first flattened task whose id is "{task_id}"
                    set subTasks to every task of parentTask
                    
                    repeat with t in subTasks
                        set taskID to id of t
                        set taskName to name of t
                        set taskNote to note of t
                        set isCompleted to completed of t
                        
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
                        
                        set output to output & taskID & "||" & taskName & "||" & taskNote & "||" & isCompleted & "||" & dd & "||" & projName & "\\n"
                    end repeat
                    
                    return output
                on error
                    return ""
                end try
            end tell
        end tell
        '''
        
        result = subprocess.run(["osascript", "-e", as_script], capture_output=True, text=True, timeout=10)
        
        if result.returncode != 0:
            print(f"AppleScript error: {result.stderr.strip()}")
            print("Falling back to empty list...")
            return []
        
        # Parse the output
        tasks = []
        output = result.stdout.strip()
        
        if not output:
            print("No subtasks found or task does not exist.")
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
        
    except Exception as e:
        print(f"Error fetching subtasks: {str(e)}")
        print("Falling back to empty list...")
        return []

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
    
    try:
        # Check if Evernote is running and available
        check_script = '''
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
        '''
        
        check_result = subprocess.run(["osascript", "-e", check_script], capture_output=True, text=True)
        if check_result.returncode != 0 or not check_result.stdout.strip().startswith("true"):
            print("Evernote is not available or could not be launched.")
            return False
        
        # Escape strings for AppleScript
        escaped_title = escape_applescript_string(title)
        escaped_content = escape_applescript_string(content)
        escaped_notebook = escape_applescript_string(notebook)
        
        # Prepare tags for AppleScript
        tags_script = ""
        if tags and len(tags) > 0:
            tag_strings = []
            for tag in tags:
                escaped_tag = escape_applescript_string(tag)
                tag_strings.append(f'"{escaped_tag}"')
            
            tags_script = f'''
            -- Add tags
            set tagNames to {{{", ".join(tag_strings)}}}
            repeat with tagName in tagNames
                tell newNote to assign tag tagName
            end repeat
            '''
        
        # Build the AppleScript to create a note in Evernote
        as_script = f'''
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
                
                {tags_script}
                
                return "true"
            on error errMsg
                return "false: " & errMsg
            end try
        end tell
        '''
        
        result = subprocess.run(["osascript", "-e", as_script], capture_output=True, text=True, timeout=20)
        
        if result.returncode != 0:
            print(f"AppleScript error: {result.stderr.strip()}")
            return False
        
        output = result.stdout.strip()
        if output.startswith("false:"):
            print(f"Evernote error: {output[6:]}")
            return False
        
        print(f"Successfully exported note '{title}' to Evernote in notebook '{notebook}'.")
        return True
        
    except Exception as e:
        print(f"Error exporting to Evernote: {str(e)}")
        return False