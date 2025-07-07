import json
from omnifocus_api import apple_script_client
from ai_integration.utils.format_utils import format_task_list
import subprocess
import tempfile
import os
from typing import Optional, List, Dict, Any
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.data_loading import load_and_prepare_omnifocus_data, query_prepared_data, get_latest_json_export_path

def handle_list(args):
    """
    Lists tasks from the JSON export, optionally filtered by project and/or search text.
    """
    file = getattr(args, 'file', None) or get_latest_json_export_path()
    data = load_and_prepare_omnifocus_data(file)
    if not data or not data.get("all_tasks"):
        print(f"No tasks found in {file}")
        return
    project = getattr(args, 'project', None)
    search = getattr(args, 'search', None)
    tasks = [t for t in data["all_tasks"] if (not project or t.get("projectId") == project)]
    if search:
        tasks = [t for t in tasks if search.lower() in t.get("name", "").lower() or search.lower() in t.get("note", "").lower()]
    if getattr(args, 'json', False):
        print(json.dumps(tasks, indent=2))
    else:
        for t in tasks:
            print(f"- {t.get('name')} (ID: {t.get('id')})")

def generate_list_live_tasks_applescript(project_name: str) -> str:
    """Generates AppleScript to list tasks from a specific project with their details."""
    # Sanitize project_name for AppleScript string
    s_project_name = project_name.replace('\\', '\\\\').replace('"', '\\"')
    
    script = f"""
    set taskList to {{}}
    tell application "OmniFocus"
        tell default document
            try
                set theProject to first flattened project whose name is "{s_project_name}"
            on error
                return "Error: Project '{s_project_name}' not found."
            end try
            
            if theProject is not missing value then
                tell theProject
                    repeat with aTask in (every task where completed is false)
                        set end of taskList to {{id:(id of aTask as string), name:(name of aTask as string), completed:false}}
                    end repeat
                    repeat with aTask in (every task where completed is true)
                        set end of taskList to {{id:(id of aTask as string), name:(name of aTask as string), completed:true}}
                    end repeat
                end tell
            else
                 return "Error: Project '{s_project_name}' reference is missing value after find attempt."
            end if
        end tell
    end tell
    return taskList
    """
    return script

def parse_applescript_task_list_output(output_str: str) -> List[Dict[str, Any]]:
    """Parses the structured string output from the AppleScript list into a Python list of dicts."""
    # AppleScript returns a list of records like: {{id:"id1", name:"name1", completed:true}, {id:"id2", ...}}
    # This is a naive parser. A robust one would handle escaping and edge cases.
    tasks = []
    if output_str.startswith("Error:") or not output_str.startswith("{{") or not output_str.endswith("}}"):
        if output_str.startswith("Error:"):
            print(output_str) # Print the error message from AppleScript
        else:
            print(f"Warning: Unexpected AppleScript output format: {output_str}")
        return tasks

    # Remove outer {{ and }}
    content = output_str[2:-2]
    # Split by record separator: "}, {" (AppleScript might use ", " or similar between records)
    # A common AppleScript list-of-records string form is item1, item2, item3 where item is {prop1:val1, prop2:val2}
    # Let's assume a simpler split for now, this needs to be robust based on actual AS output.
    # If AS returns "{{id:x, name:y}, {id:a, name:b}}", splitting by "}, {" is one way.

    # A more reliable way if AppleScript can return it, is line-separated items or JSON.
    # For now, this parser is a placeholder and will likely fail.
    # We will rely on printing the raw string from AppleScript for now.
    # TODO: Implement proper parsing based on actual AppleScript list-of-records format.
    print("Raw AppleScript output (needs parsing):")
    print(output_str)
    return tasks # Placeholder

def handle_list_live_tasks_in_project(args):
    project_name = args.project_name
    applescript_command = generate_list_live_tasks_applescript(project_name)

    print(f"\nAttempting to list tasks live from project: '{project_name}'")
    print("Generated AppleScript (for review):")
    print(applescript_command + "\n")

    execute_omnifocus_applescript = None
    try:
        from omnifocus_api.apple_script_client import execute_omnifocus_applescript
    except ImportError:
        print("Info: Using direct osascript call for AppleScript execution.")

    raw_result = ""
    try:
        if execute_omnifocus_applescript:
            raw_result = execute_omnifocus_applescript(applescript_command)
        else:
            tmp_file_path = None
            try:
                with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.applescript') as tmp_script_file:
                    tmp_script_file.write(applescript_command)
                    tmp_file_path = tmp_script_file.name
                process = subprocess.run(["osascript", tmp_file_path], capture_output=True, text=True, check=False)
                if process.returncode == 0:
                    raw_result = process.stdout.strip()
                else:
                    raw_result = f"Error: osascript failed. STDERR: {process.stderr.strip()}"
            finally:
                if tmp_file_path and os.path.exists(tmp_file_path):
                    os.remove(tmp_file_path)
        
        if raw_result.startswith("Error:"):
            print(f"Failed to list tasks: {raw_result}")
        elif not raw_result:
            print("No tasks found in the project or project is empty.")
        else:
            # For now, just print the raw structured output from AppleScript
            # Proper parsing into a list of dicts would go here via parse_applescript_task_list_output
            print("Live tasks from OmniFocus (raw AppleScript output):")
            print(raw_result)
            # Example of how it might be used if parsing worked:
            # parsed_tasks = parse_applescript_task_list_output(raw_result)
            # if parsed_tasks:
            #     for task_info in parsed_tasks:
            #         print(f"- ID: {task_info.get('id')}, Name: {task_info.get('name')}, Completed: {task_info.get('completed')}")
            # else:
            #     print("Could not parse task list from AppleScript output or no tasks found.")

    except Exception as e:
        print(f"An unexpected error occurred: {e}")

def generate_list_live_projects_applescript() -> str:
    """Generates AppleScript to list all projects with ID, name, folder, and status, returning a list of formatted strings."""
    script = f"""
    set projectStringList to {{}} -- Initialize an empty AppleScript list
    tell application "OmniFocus"
        tell default document
            repeat with aProject in (every flattened project)
                set projectId to id of aProject as string
                set projectName to name of aProject as string
                
                set projectStatusText to "unknown"
                try
                    set projStatus to status of aProject
                    if projStatus is active then
                        set projectStatusText to "active"
                    else if projStatus is on hold then
                        set projectStatusText to "on hold"
                    else if projStatus is done then
                        set projectStatusText to "completed"
                    else if projStatus is dropped then
                        set projectStatusText to "dropped"
                    end if
                on error
                    set projectStatusText to "error_getting_status"
                end try

                set folderName to ""
                try
                    if class of container of aProject is folder then
                        set folderName to name of container of aProject
                    end if
                on error
                    set folderName to "error_getting_folder"
                end try
                
                -- Create a delimited string for each project
                set projectInfoString to "ID=" & projectId & "|Name=" & projectName & "|Status=" & projectStatusText & "|Folder=" & folderName
                set end of projectStringList to projectInfoString
            end repeat
        end tell
    end tell
    return projectStringList -- Return the list of strings
    """
    return script

def handle_list_live_projects(args):
    applescript_command = generate_list_live_projects_applescript()
    print("\nAttempting to list all projects with details live from OmniFocus...")
    # print("Generated AppleScript (for review):") # Optional: can be verbose
    # print(applescript_command + "\n")

    execute_omnifocus_applescript = None
    try:
        from omnifocus_api.apple_script_client import execute_omnifocus_applescript
    except ImportError:
        print("Info: Using direct osascript call for AppleScript execution.")

    raw_result = ""
    try:
        if execute_omnifocus_applescript:
            raw_result = execute_omnifocus_applescript(applescript_command)
        else:
            # ... (osascript execution using temp file as before) ...
            tmp_file_path = None
            try:
                with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.applescript') as tmp_script_file:
                    tmp_script_file.write(applescript_command)
                    tmp_file_path = tmp_script_file.name
                process = subprocess.run(["osascript", tmp_file_path], capture_output=True, text=True, check=False)
                if process.returncode == 0:
                    raw_result = process.stdout.strip()
                else:
                    raw_result = f"Error: osascript failed. STDERR: {process.stderr.strip()}"
            finally:
                if tmp_file_path and os.path.exists(tmp_file_path):
                    os.remove(tmp_file_path)
        
        if raw_result.startswith("Error:"):
            print(f"Failed to list projects: {raw_result}")
        elif not raw_result:
            print("No projects found or database is empty.")
        else:
            print("\nLive projects from OmniFocus:")
            project_strings = raw_result.split(", ") # AppleScript lists of strings are comma-space delimited when coerced to text
            if not project_strings or (len(project_strings) == 1 and project_strings[0] == ""): 
                print("No projects found or an issue with parsing the project list.")
            else: 
                for project_str in project_strings:
                    if not project_str.strip(): continue # Skip empty strings if any
                    parts = {}
                    try:
                        for item in project_str.split("|"):
                            key_value = item.split("=", 1)
                            if len(key_value) == 2:
                                parts[key_value[0]] = key_value[1]
                            elif key_value[0]: # Handle case like 'Folder=' (empty folder name)
                                parts[key_value[0]] = ""
                        
                        project_id = parts.get("ID", "N/A")
                        project_name = parts.get("Name", "Unnamed Project")
                        project_status = parts.get("Status", "unknown")
                        folder_name = parts.get("Folder", "")
                        
                        output_line = f"- {project_name} (ID: {project_id}) [Status: {project_status}]"
                        if folder_name and folder_name != "error_getting_folder":
                            output_line += f" [Folder: {folder_name}]"
                        elif folder_name == "error_getting_folder":
                            output_line += f" [Folder: Error retrieving]"
                        print(output_line)
                    except Exception as e_parse:
                        print(f"Error parsing project string '{project_str}': {e_parse}")
                        print(f"Original string part: {project_str}") # Print problematic part

    except Exception as e:
        print(f"An unexpected error occurred: {e}")

