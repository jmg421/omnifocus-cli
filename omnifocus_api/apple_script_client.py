"""Unified AppleScript execution helper for OmniFocus CLI.

This module centralises the logic for running AppleScript snippets on macOS.
Other modules can simply import and call :pyfunc:`execute_omnifocus_applescript`
without worrying about whether the *unified runner* (``scripts/run_script.py``)
should be used or the system ``osascript`` command.

If the environment variable ``OF_RUNNER_V2`` is set to ``"1"`` we will invoke
``scripts/run_script.py`` with the ``--script`` flag.  Otherwise we default to
``osascript`` for backwards-compatibility.

Returned output is *stdout* with leading/trailing whitespace stripped.  Any
non-zero exit status raises :class:`RuntimeError` with stderr attached.
"""
from __future__ import annotations

import os
import pathlib
import subprocess
import tempfile
from typing import Final
import datetime

__all__: Final = ["execute_omnifocus_applescript"]


class AppleScriptExecutionError(RuntimeError):
    """Raised when the AppleScript (runner) returns a non-zero exit code."""


def _write_temp_applescript(script: str) -> str:
    """Write *script* to a temporary *.applescript* file and return its path."""
    tmp_file = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".applescript")
    tmp_file.write(script)
    tmp_file.flush()
    tmp_file.close()
    return tmp_file.name


def execute_omnifocus_applescript(script: str) -> str:  # noqa: D401
    """Run an AppleScript snippet and return its *stdout* as ``str``.

    The helper chooses between the *unified runner* and the system ``osascript``
    based on the ``OF_RUNNER_V2`` environment variable.
    """

    # Write the AppleScript to a temporary file.
    script_path = _write_temp_applescript(script)

    try:
        if os.getenv("OF_RUNNER_V2") == "1":
            runner_path = pathlib.Path(__file__).resolve().parents[2] / "scripts" / "run_script.py"
            cmd = ["python3", str(runner_path), "--script", script_path]
        else:
            cmd = ["osascript", script_path]

        process = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if process.returncode != 0:
            raise AppleScriptExecutionError(
                f"AppleScript execution failed (code {process.returncode}): {process.stderr.strip()}"
            )

        return process.stdout.strip()
    finally:
        # Ensure the temporary file is always removed.
        try:
            os.remove(script_path)
        except FileNotFoundError:
            pass


def fetch_inbox_tasks():
    """Fetch all inbox tasks from OmniFocus as a list of dicts."""
    script = '''
tell application "OmniFocus"
    tell default document
        set output to ""
        set taskList to every inbox task
        repeat with t in taskList
            set taskID to id of t
            set taskName to name of t
            set taskNote to note of t
            set isFlagged to flagged of t
            set isCompleted to completed of t
            if due date of t is missing value then
                set dd to ""
            else
                set dd to due date of t as string
            end if
            set output to output & taskID & "||" & taskName & "||" & taskNote & "||" & isFlagged & "||" & isCompleted & "||" & dd & "\n"
        end repeat
        return output
    end tell
end tell
'''
    result = execute_omnifocus_applescript(script)
    tasks = []
    for line in result.strip().split("\n"):
        if not line.strip():
            continue
        parts = line.split("||")
        if len(parts) >= 6:
            tasks.append({
                "id": parts[0],
                "name": parts[1],
                "note": parts[2],
                "flagged": parts[3] == "true",
                "completed": parts[4] == "true",
                "due_date": parts[5] if parts[5] else None
            })
    return tasks

def fetch_flagged_tasks():
    """Fetch all flagged tasks from OmniFocus as a list of dicts."""
    script = '''
tell application "OmniFocus"
    tell default document
        set output to ""
        set taskList to every flattened task whose flagged is true
        repeat with t in taskList
            set taskID to id of t
            set taskName to name of t
            set taskNote to note of t
            set isFlagged to flagged of t
            set isCompleted to completed of t
            if due date of t is missing value then
                set dd to ""
            else
                set dd to due date of t as string
            end if
            set output to output & taskID & "||" & taskName & "||" & taskNote & "||" & isFlagged & "||" & isCompleted & "||" & dd & "\n"
        end repeat
        return output
    end tell
end tell
'''
    result = execute_omnifocus_applescript(script)
    tasks = []
    for line in result.strip().split("\n"):
        if not line.strip():
            continue
        parts = line.split("||")
        if len(parts) >= 6:
            tasks.append({
                "id": parts[0],
                "name": parts[1],
                "note": parts[2],
                "flagged": parts[3] == "true",
                "completed": parts[4] == "true",
                "due_date": parts[5] if parts[5] else None
            })
    return tasks

def fetch_overdue_tasks():
    """Fetch all overdue tasks from OmniFocus as a list of dicts."""
    script = '''
tell application "OmniFocus"
    tell default document
        set output to ""
        set nowDate to current date
        set taskList to every flattened task whose due date is not missing value and due date < nowDate and completed is false
        repeat with t in taskList
            set taskID to id of t
            set taskName to name of t
            set taskNote to note of t
            set isFlagged to flagged of t
            set isCompleted to completed of t
            set dd to due date of t as string
            set output to output & taskID & "||" & taskName & "||" & taskNote & "||" & isFlagged & "||" & isCompleted & "||" & dd & "\n"
        end repeat
        return output
    end tell
end tell
'''
    result = execute_omnifocus_applescript(script)
    tasks = []
    for line in result.strip().split("\n"):
        if not line.strip():
            continue
        parts = line.split("||")
        if len(parts) >= 6:
            tasks.append({
                "id": parts[0],
                "name": parts[1],
                "note": parts[2],
                "flagged": parts[3] == "true",
                "completed": parts[4] == "true",
                "due_date": parts[5] if parts[5] else None
            })
    return tasks

def fetch_project_names() -> list:
    """Fetch all project names from OmniFocus as a list of strings."""
    script = '''
tell application "OmniFocus"
    tell default document
        set output to ""
        set projectList to every flattened project
        repeat with p in projectList
            set projectName to name of p
            set output to output & projectName & "\n"
        end repeat
        return output
    end tell
end tell
'''
    result = execute_omnifocus_applescript(script)
    return [line.strip() for line in result.strip().split("\n") if line.strip()]

def _to_applescript_date(date_str: str) -> str:
    """Convert 'YYYY-MM-DD HH:MM:SS' to AppleScript's expected date format."""
    try:
        dt = datetime.datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
        # Format: 'Tuesday, July 16, 2025 at 11:59:00 PM'
        return dt.strftime("%A, %B %d, %Y at %I:%M:%S %p")
    except Exception as e:
        print(f"Date conversion error: {e}")
        return date_str

def set_task_due_date(task_id: str, date_str: str) -> bool:
    applescript_date = _to_applescript_date(date_str)
    script = f'''
tell application "OmniFocus"
    tell default document
        try
            set theTask to first flattened task whose id is "{task_id}"
                    set due date of theTask to date "{applescript_date}"
        return "SUCCESS"
    on error errMsg number errNum
        if errNum is -1728 or errNum is -1719 then
            return "NOT_FOUND"
        else
            return "ERROR: " & errMsg
        end if
        end try
    end tell
end tell
'''
    try:
        result = execute_omnifocus_applescript(script)
        if result == "SUCCESS":
            return True
        elif result == "NOT_FOUND":
            print(f"ℹ️  No matching OmniFocus task found with ID: {task_id}")
            return False
        else:
            print(f"AppleScript error: {result}\nDate string: {date_str}\nAppleScript date: {applescript_date}")
            return False
    except Exception as e:
        print(f"AppleScript error: {e}\nDate string: {date_str}\nAppleScript date: {applescript_date}")
        return False

def set_task_defer_date(task_id: str, date_str: str) -> bool:
    applescript_date = _to_applescript_date(date_str)
    script = f'''
tell application "OmniFocus"
    tell default document
        try
            set theTask to first flattened task whose id is "{task_id}"
                    set defer date of theTask to date "{applescript_date}"
        return "SUCCESS"
    on error errMsg number errNum
        if errNum is -1728 or errNum is -1719 then
            return "NOT_FOUND"
        else
            return "ERROR: " & errMsg
        end if
        end try
    end tell
end tell
'''
    try:
        result = execute_omnifocus_applescript(script)
        if result == "SUCCESS":
            return True
        elif result == "NOT_FOUND":
            print(f"ℹ️  No matching OmniFocus task found with ID: {task_id}")
            return False
        else:
            print(f"AppleScript error: {result}\nDate string: {date_str}\nAppleScript date: {applescript_date}")
            return False
    except Exception as e:
        print(f"AppleScript error: {e}\nDate string: {date_str}\nAppleScript date: {applescript_date}")
        return False

def move_task_to_project(task_id: str, project_name: str) -> bool:
    """Move a task to a project using AppleScript."""
    
    # Handle [NEW] project creation
    if project_name.startswith("[NEW] "):
        actual_project_name = project_name[6:]  # Remove "[NEW] " prefix
        applescript = f'''
tell application "OmniFocus"
    tell default document
        try
            set theTask to first flattened task whose id is "{task_id}"
            
            -- Try to find existing project first
            set theProject to missing value
            try
                set theProject to first flattened project whose name is "{actual_project_name}"
            on error
                -- Project doesn't exist, create it
                set theProject to make new project with properties {{name:"{actual_project_name}"}}
            end try
            
            move theTask to end of tasks of theProject
            return "SUCCESS"
        on error errMsg number errNum
            if errNum is -1728 or errNum is -1719 then
                return "TASK_NOT_FOUND"
            else
                return "ERROR: " & errMsg
            end if
        end try
    end tell
end tell
'''
    else:
        # Existing project lookup
        applescript = f'''
tell application "OmniFocus"
    tell default document
        try
            set theTask to first flattened task whose id is "{task_id}"
            set theProject to first flattened project whose name is "{project_name}"
            move theTask to end of tasks of theProject
            return "SUCCESS"
        on error errMsg number errNum
            if errNum is -1728 or errNum is -1719 then
                return "TASK_NOT_FOUND"
            else if errNum is -1729 then
                return "PROJECT_NOT_FOUND"
            else
                return "ERROR: " & errMsg
            end if
        end try
    end tell
end tell
'''
    
    try:
        result = execute_omnifocus_applescript(applescript)
        if result == "SUCCESS":
            return True
        elif result == "TASK_NOT_FOUND":
            print(f"ℹ️  No matching OmniFocus task found with ID: {task_id}")
            return False
        elif result == "PROJECT_NOT_FOUND":
            print(f"ℹ️  No matching OmniFocus project found with name: {project_name}")
            return False
        else:
            print(f"[AppleScript Error] Could not move task {task_id} to project {project_name}: {result}")
            return False
    except Exception as e:
        print(f"[AppleScript Error] Could not move task {task_id} to project {project_name}: {e}")
        return False

def set_task_name(task_id: str, new_name: str) -> bool:
    """Set the name of a task using AppleScript."""
    script = f'''
tell application "OmniFocus"
    tell default document
        try
            set theTask to first flattened task whose id is "{task_id}"
                    set name of theTask to "{new_name}"
        return "SUCCESS"
    on error errMsg number errNum
        if errNum is -1728 or errNum is -1719 then
            return "NOT_FOUND"
        else
            return "ERROR: " & errMsg
        end if
        end try
    end tell
end tell
'''
    try:
        result = execute_omnifocus_applescript(script)
        if result == "SUCCESS":
            return True
        elif result == "NOT_FOUND":
            print(f"ℹ️  No matching OmniFocus task found with ID: {task_id}")
            return False
        else:
            print(f"[AppleScript Error] Could not set task name for {task_id}: {result}")
            return False
    except Exception as e:
        print(f"[AppleScript Error] Could not set task name for {task_id}: {e}")
        return False

def set_task_note(task_id: str, new_note: str) -> bool:
    """Set the note of a task using AppleScript."""
    script = f'''
tell application "OmniFocus"
    tell default document
        try
            set theTask to first flattened task whose id is "{task_id}"
                    set note of theTask to "{new_note}"
        return "SUCCESS"
    on error errMsg number errNum
        if errNum is -1728 or errNum is -1719 then
            return "NOT_FOUND"
        else
            return "ERROR: " & errMsg
        end if
        end try
    end tell
end tell
'''
    try:
        result = execute_omnifocus_applescript(script)
        if result == "SUCCESS":
            return True
        elif result == "NOT_FOUND":
            print(f"ℹ️  No matching OmniFocus task found with ID: {task_id}")
            return False
        else:
            print(f"[AppleScript Error] Could not set task note for {task_id}: {result}")
            return False
    except Exception as e:
        print(f"[AppleScript Error] Could not set task note for {task_id}: {e}")
        return False

def complete_task(task_id: str) -> bool:
    """Mark a task as completed using AppleScript."""
    script = f'''
tell application "OmniFocus"
    tell default document
        try
            set theTask to first flattened task whose id is "{task_id}"
            
            -- Check if task is in inbox
            set isInInbox to true
            try
                if containing project of theTask is not missing value then
                    set isInInbox to false
                end if
            on error
                -- Assume it's in inbox if we can't determine
                set isInInbox to true
            end try
            
            if isInInbox then
                -- Move to Reference project first, then complete
                set refProject to missing value
                try
                    set refProject to first flattened project whose name is "Reference"
                on error
                    set refProject to make new project with properties {{name:"Reference"}}
                end try
                
                move theTask to end of tasks of refProject
                delay 0.2
                
                -- Re-fetch and complete
                set taskToComplete to first flattened task of refProject whose id is "{task_id}"
                mark complete taskToComplete
            else
                -- Task is already in a project, complete directly
                mark complete theTask
            end if
            return "SUCCESS"
        on error errMsg number errNum
            if errNum is -1728 or errNum is -1719 then
                return "NOT_FOUND"
            else
                return "ERROR: " & errMsg
            end if
        end try
    end tell
end tell
'''
    try:
        result = execute_omnifocus_applescript(script)
        if result == "SUCCESS":
            return True
        elif result == "NOT_FOUND":
            print(f"ℹ️  No matching OmniFocus task found with ID: {task_id}")
            return False
        else:
            print(f"[AppleScript Error] Could not complete task {task_id}: {result}")
            return False
    except Exception as e:
        print(f"[AppleScript Error] Could not complete task {task_id}: {e}")
        return False

def delete_task(task_id: str) -> bool:
    """Delete a task using AppleScript."""
    script = f'''
tell application "OmniFocus"
    tell default document
        try
            set theTask to first flattened task whose id is "{task_id}"
            delete theTask
            return "SUCCESS"
        on error errMsg number errNum
            if errNum is -1728 or errNum is -1719 then
                return "NOT_FOUND"
            else
                return "ERROR: " & errMsg
            end if
        end try
    end tell
end tell
'''
    try:
        result = execute_omnifocus_applescript(script)
        if result == "SUCCESS":
            return True
        elif result == "NOT_FOUND":
            print(f"ℹ️  No matching OmniFocus task found with ID: {task_id}")
            return False
        else:
            print(f"[AppleScript Error] Could not delete task {task_id}: {result}")
            return False
    except Exception as e:
        print(f"[AppleScript Error] Could not delete task {task_id}: {e}")
        return False

def unflag_task(task_id: str) -> bool:
    """Remove flag from a task using AppleScript."""
    script = f'''
tell application "OmniFocus"
    tell default document
        try
            set theTask to first flattened task whose id is "{task_id}"
            set flagged of theTask to false
            return "SUCCESS"
        on error errMsg number errNum
            if errNum is -1728 or errNum is -1719 then
                return "NOT_FOUND"
            else
                return "ERROR: " & errMsg
            end if
        end try
    end tell
end tell
'''
    try:
        result = execute_omnifocus_applescript(script)
        if result == "SUCCESS":
            return True
        elif result == "NOT_FOUND":
            print(f"ℹ️  No matching OmniFocus task found with ID: {task_id}")
            return False
        else:
            print(f"[AppleScript Error] Could not unflag task {task_id}: {result}")
            return False
    except Exception as e:
        print(f"[AppleScript Error] Could not unflag task {task_id}: {e}")
        return False

def fetch_subtasks(task_id: str) -> list:
    """Fetch subtasks of a task using AppleScript."""
    script = f'''
tell application "OmniFocus"
    tell default document
        try
            set output to ""
            set theTask to first flattened task whose id is "{task_id}"
            set subtaskList to tasks of theTask
            repeat with subtask in subtaskList
                set subtaskID to id of subtask
                set subtaskName to name of subtask
                set output to output & subtaskID & "||" & subtaskName & "\n"
            end repeat
            return output
        on error errMsg number errNum
            if errNum is -1728 or errNum is -1719 then
                return "NOT_FOUND"
            else
                return "ERROR: " & errMsg
            end if
        end try
    end tell
end tell
'''
    try:
        result = execute_omnifocus_applescript(script)
        if result == "NOT_FOUND":
            print(f"ℹ️  No matching OmniFocus task found with ID: {task_id}")
            return []
        elif result.startswith("ERROR:"):
            print(f"[AppleScript Error] Could not fetch subtasks for {task_id}: {result}")
            return []
        
        subtasks = []
        for line in result.strip().split("\n"):
            if not line.strip():
                continue
            parts = line.split("||")
            if len(parts) >= 2:
                subtasks.append({
                    "id": parts[0],
                    "name": parts[1]
                })
        return subtasks
    except Exception as e:
        print(f"[AppleScript Error] Could not fetch subtasks for {task_id}: {e}")
        return []

def fetch_adjacent_tasks_context(task_id: str, context_size: int = 2) -> dict:
    """Fetch adjacent tasks with their project context for temporal analysis."""
    script = f'''
tell application "OmniFocus"
    tell default document
        set output to ""
        set allInboxTasks to every inbox task
        set targetIndex to 0
        set targetFound to false
        
        -- Find the target task index
        repeat with i from 1 to count of allInboxTasks
            if id of item i of allInboxTasks is "{task_id}" then
                set targetIndex to i
                set targetFound to true
                exit repeat
            end if
        end repeat
        
        if targetFound then
            -- Get adjacent tasks (before and after)
            set startIndex to (targetIndex - {context_size})
            if startIndex < 1 then
                set startIndex to 1
            end if
            
            set endIndex to (targetIndex + {context_size})
            if endIndex > count of allInboxTasks then
                set endIndex to count of allInboxTasks
            end if
            
            repeat with i from startIndex to endIndex
                set currentTask to item i of allInboxTasks
                set taskID to id of currentTask
                set taskName to name of currentTask
                set taskNote to note of currentTask
                
                -- Get project context if task is not in inbox
                set projectContext to "INBOX"
                try
                    set containingProject to containing project of currentTask
                    if containingProject is not missing value then
                        set projectContext to name of containingProject
                    end if
                on error
                    -- Task is in inbox or error occurred
                    set projectContext to "INBOX"
                end try
                
                -- Mark if this is the target task
                set isTarget to "false"
                if i is targetIndex then
                    set isTarget to "true"
                end if
                
                set output to output & taskID & "||" & taskName & "||" & taskNote & "||" & projectContext & "||" & isTarget & "\n"
            end repeat
        end if
        
        return output
    end tell
end tell
'''
    try:
        result = execute_omnifocus_applescript(script)
        adjacent_tasks = []
        target_task = None
        
        for line in result.strip().split("\n"):
            if not line.strip():
                continue
            parts = line.split("||")
            if len(parts) >= 5:
                task_info = {
                    "id": parts[0],
                    "name": parts[1],
                    "note": parts[2],
                    "project_context": parts[3],
                    "is_target": parts[4] == "true"
                }
                adjacent_tasks.append(task_info)
                
                if task_info["is_target"]:
                    target_task = task_info
        
        return {
            "target_task": target_task,
            "adjacent_tasks": adjacent_tasks,
            "context_size": context_size
        }
    except Exception as e:
        print(f"[AppleScript Error] Could not fetch adjacent tasks for {task_id}: {e}")
        return {
            "target_task": None,
            "adjacent_tasks": [],
            "context_size": context_size
        }
