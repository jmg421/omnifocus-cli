"""Task-related operations for OmniFocus."""
from typing import List, Optional
from .apple_script_client import execute_omnifocus_applescript  # Unified helper
from .data_models import OmniFocusTask
from .utils import escape_applescript_string

def complete_task(task_id: str) -> bool:
    """Mark task as completed, moving to Reference project if in inbox."""
    as_script = f'''
    tell application "OmniFocus"
        try
            tell default document
                set theTask to first flattened task whose id is "{task_id}"
                
                -- Function to process a task
                on processTask(taskToProcess)
                    -- Check if it's an inbox task
                    if exists (every inbox task whose id is (id of taskToProcess)) then
                        try
                            set refProject to first flattened project whose name is "Reference"
                        on error
                            set refProject to make new project with properties {{name:"Reference"}}
                        end try
                        move taskToProcess to end of tasks of refProject
                        delay 0.1
                    end if
                    set completed of taskToProcess to true
                end processTask
                
                if exists theTask then
                    repeat with subTask in (every task of theTask)
                        my processTask(subTask)
                    end repeat
                    my processTask(theTask)
                    return "true"
                end if
                return "false: Task not found"
            end tell
        on error errMsg
            return "false: " & errMsg
        end try
    end tell
    '''
    
    try:
        output = execute_omnifocus_applescript(as_script)
        if output.startswith("false:"):
            print(f"OmniFocus error: {output[6:]}")
            return False
        return output.lower() == "true"
    except Exception as e:
        print(f"Python error: {str(e)}")
        return False

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
    
    try:
        script_output = execute_omnifocus_applescript(as_script)
    except Exception:
        script_output = ""
    tasks = []
    for line in script_output.strip().split("\n"):
        if not line.strip():
            continue
        parts = line.split("||")
        if len(parts) >= 5:
            task_id, name, note, completed_str, due_date_str = parts
            tasks.append(OmniFocusTask(
                id=task_id,
                name=name,
                note=note,
                completed=(completed_str == "true"),
                due_date=due_date_str if due_date_str else None
            ))
    return tasks 