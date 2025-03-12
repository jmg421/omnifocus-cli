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


def fetch_tasks(project_name: Optional[str] = None, search_text: Optional[str] = None) -> List[OmniFocusTask]:
    """
    Fetch tasks from OmniFocus. 
    If project_name is provided, only fetch tasks from that project.
    If search_text is provided, only fetch tasks containing that text (case-insensitive).
    Returns a list of OmniFocusTask objects.
    """
    # Escape inputs for AppleScript
    escaped_project = escape_applescript_string(project_name) if project_name else ""
    escaped_search = escape_applescript_string(search_text) if search_text else ""
    
    as_script = '''
    tell application "OmniFocus"
        tell default document
            set output to ""
            
            -- Get tasks based on project filter
            if "PROJECTNAME" is not "" then
                try
                    set theProject to first flattened project where name is "PROJECTNAME"
                    set theTasks to every flattened task of theProject
                on error
                    return ""
                end try
            else
                set theTasks to every flattened task
            end if
            
            -- Process each task
            repeat with t in theTasks
                try
                    set taskName to name of t
                    
                    -- Apply search filter if provided
                    if "SEARCHTEXT" is not "" then
                        if taskName does not contain "SEARCHTEXT" then
                            continue
                        end if
                    end if
                    
                    -- Get task details
                    set taskID to id of t
                    set taskNote to note of t
                    set isCompleted to completed of t
                    
                    if due date of t is missing value then
                        set dd to ""
                    else
                        set dd to ((due date of t) as «class isot» as string)
                    end if
                    
                    -- Build the output line
                    set taskLine to taskID & "||" & taskName & "||" & taskNote & "||" & dd & "||" & isCompleted
                    if output is "" then
                        set output to taskLine
                    else
                        set output to output & linefeed & taskLine
                    end if
                end try
            end repeat
            
            return output
        end tell
    end tell
    '''.replace("PROJECTNAME", escaped_project).replace("SEARCHTEXT", escaped_search)

    try:
        result = subprocess.run(
            ["osascript", "-e", as_script], 
            capture_output=True, 
            text=True,
            timeout=5  # Increased timeout for larger projects
        )
        
        if result.returncode != 0:
            print(f"Error accessing OmniFocus: {result.stderr.strip()}")
            return []
            
        tasks = []
        lines = result.stdout.strip().split("\n")
        
        if not lines or (len(lines) == 1 and not lines[0]):
            return []
            
        for line in lines:
            if not line:
                continue
                
            parts = line.split("||")
            if len(parts) >= 5:
                task_id, name, note, due_date, completed = parts[:5]
                tasks.append(OmniFocusTask(
                    id=task_id,
                    name=name,
                    note=note,
                    due_date=due_date if due_date else None,
                    completed=completed.lower() == "true"
                ))
        
        return tasks
        
    except subprocess.TimeoutExpired:
        print("Error: OmniFocus is not responding")
        return []
    except Exception as e:
        print(f"Error fetching tasks: {str(e)}")
        return []


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
    as_script = '''
    tell application "OmniFocus"
        tell default document
            set output to ""
            set flaggedTasks to every flattened task where flagged is true
            
            repeat with t in flaggedTasks
                set taskID to id of t
                set taskName to name of t
                set taskNote to note of t
                set isCompleted to completed of t
                if due date of t is missing value then
                    set dd to ""
                else
                    set dd to due date of t as string
                end if
                
                try
                    set proj to name of containing project of t
                on error
                    set proj to ""
                end try
                
                set output to output & taskID & \"||\" & taskName & \"||\" & taskNote & \"||\" & isCompleted & \"||\" & dd & \"||\" & proj & \"\\n\"
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
    as_script = '''
    tell application "OmniFocus"
        tell default document
            set output to ""
            set today to current date
            set overdueTask to every flattened task where (due date is not missing value and due date is less than today and completed is false)
            
            repeat with t in overdueTask
                set taskID to id of t
                set taskName to name of t
                set taskNote to note of t
                set isCompleted to completed of t
                if due date of t is missing value then
                    set dd to ""
                else
                    set dd to due date of t as string
                end if
                
                try
                    set proj to name of containing project of t
                on error
                    set proj to ""
                end try
                
                set output to output & taskID & \"||\" & taskName & \"||\" & taskNote & \"||\" & isCompleted & \"||\" & dd & \"||\" & proj & \"\\n\"
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
    as_script = f'''
    tell application "OmniFocus"
        tell default document
            try
                set theTask to first flattened task whose id is "{task_id}"
                delete theTask
                return "true"
            on error
                return "false"
            end try
        end tell
    end tell
    '''
    
    result = subprocess.run(["osascript", "-e", as_script], capture_output=True, text=True)
    return result.returncode == 0 and result.stdout.strip() == "true"

def unflag_task(task_id: str) -> bool:
    """Remove flag from a task."""
    as_script = f'''
    tell application "OmniFocus"
        tell default document
            try
                set theTask to first flattened task whose id is "{task_id}"
                set flagged of theTask to false
                return "true"
            on error
                return "false"
            end try
        end tell
    end tell
    '''
    
    result = subprocess.run(["osascript", "-e", as_script], capture_output=True, text=True)
    return result.returncode == 0 and result.stdout.strip() == "true"

def move_task_to_project(task_id: str, project_name: str) -> bool:
    """Move a task to a project."""
    escaped_project = escape_applescript_string(project_name)
    as_script = f'''
    tell application "OmniFocus"
        tell default document
            try
                set theTask to first flattened task whose id is "{task_id}"
                
                -- Find or create the project
                try
                    set theProject to first flattened project whose name is "{escaped_project}"
                on error
                    set theProject to make new project with properties {{name:"{escaped_project}"}}
                end try
                
                -- Move the task
                move theTask to end of tasks of theProject
                return "true"
            on error
                return "false"
            end try
        end tell
    end tell
    '''
    
    result = subprocess.run(["osascript", "-e", as_script], capture_output=True, text=True)
    return result.returncode == 0 and result.stdout.strip() == "true"

def set_task_due_date(task_id: str, due_date: str) -> bool:
    """Set the due date for a task."""
    escaped_date = escape_applescript_string(due_date)
    as_script = f'''
    tell application "OmniFocus"
        tell default document
            try
                set theTask to first flattened task whose id is "{task_id}"
                set due date of theTask to date "{escaped_date}"
                return "true"
            on error
                return "false"
            end try
        end tell
    end tell
    '''
    
    result = subprocess.run(["osascript", "-e", as_script], capture_output=True, text=True)
    return result.returncode == 0 and result.stdout.strip() == "true"

def fetch_subtasks(task_id: str) -> List[OmniFocusTask]:
    """Fetch all subtasks of a given task."""
    as_script = f'''
    tell application "OmniFocus"
        tell default document
            set output to ""
            set parentTask to first flattened task whose id is "{task_id}"
            set subTasks to every task of parentTask
            
            repeat with t in subTasks
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

def test_evernote_export() -> bool:
    """Test Evernote export with a simple note."""
    as_script = '''
    tell application "Evernote"
        try
            -- Create test notebook
            try
                set testNotebook to notebook "Test"
            on error
                create notebook "Test"
                set testNotebook to notebook "Test"
            end try
            
            -- Create simple note
            set testContent to "<?xml version=\\"1.0\\" encoding=\\"UTF-8\\"?><!DOCTYPE en-note SYSTEM \\"http://xml.evernote.com/pub/enml2.dtd\\"><en-note><h1>Test Note</h1><p>This is a test note from OmniFocus CLI.</p></en-note>"
            set newNote to create note with text testContent title "Test Note" notebook testNotebook
            
            -- Verify note was created
            if exists newNote then
                delete newNote
                return "true"
            end if
            return "false"
        on error errMsg
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
            print(f"Evernote error: {output[6:]}")  # Skip "false: " prefix
            return False
            
        return output.lower() == "true"
    except Exception as e:
        print(f"Python error while testing Evernote: {str(e)}")
        return False

def export_to_evernote(title: str, content: str, notebook: str = "Reference Material", tags: List[str] = None) -> bool:
    """Export content to Evernote."""
    tags = tags or []
    escaped_title = escape_applescript_string(title)
    escaped_content = escape_applescript_string(content)
    escaped_notebook = escape_applescript_string(notebook)
    escaped_tags = ", ".join(f'"{escape_applescript_string(tag)}"' for tag in tags)
    
    as_script = f'''
    tell application "Evernote"
        try
            -- Create or get notebook
            try
                set targetNotebook to notebook "{escaped_notebook}"
            on error
                create notebook "{escaped_notebook}"
                set targetNotebook to notebook "{escaped_notebook}"
            end try
            
            -- Create note with proper ENML
            set noteContent to "<?xml version=\\"1.0\\" encoding=\\"UTF-8\\"?><!DOCTYPE en-note SYSTEM \\"http://xml.evernote.com/pub/enml2.dtd\\"><en-note><div>{escaped_content}</div></en-note>"
            set newNote to create note with text noteContent title "{escaped_title}" notebook targetNotebook
            
            -- Add tags
            if "{escaped_tags}" is not "" then
                repeat with tagName in {{{escaped_tags}}}
                    try
                        assign tag tagName to newNote
                    end try
                end repeat
            end if
            
            -- Verify note was created
            if exists newNote then
                return "true"
            end if
            return "false"
        on error errMsg
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
            print(f"Evernote error: {output[6:]}")  # Skip "false: " prefix
            return False
            
        return output.lower() == "true"
    except Exception as e:
        print(f"Python error while exporting to Evernote: {str(e)}")
        return False

