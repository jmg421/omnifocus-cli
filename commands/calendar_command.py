from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from omnifocus_api import apple_script_client
from omnifocus_api.data_models import OmniFocusTask
from ai_integration.ical_integration import fetch_calendar_events, sync_with_calendar
import requests
import icalendar
import subprocess
import tempfile
import os

# Attempt to import shared utilities, if they exist in a known shared location
# If not, local_ versions will be used.
_parse_date_string_imported = False
_escape_applescript_string_imported = False
try:
    from ..ai_integration.utils.format_utils import parse_date_string as shared_parse_date_string
    _parse_date_string_imported = True
except ImportError:
    pass

try:
    from .add_command import escape_applescript_string as shared_escape_applescript_string
    _escape_applescript_string_imported = True
except ImportError:
    pass

def parse_datetime_flexible(dt_str: Optional[str]) -> Optional[datetime]:
    if not dt_str:
        return None
    try:
        return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
    except ValueError:
        try:
            return datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            try:
                return datetime.strptime(dt_str, "%Y-%m-%d")
            except ValueError:
                print(f"Warning: Could not parse date string: {dt_str}")
                return None

def handle_calendar(args):
    """
    Sync OmniFocus tasks with iCal calendars to verify reality status.
    """
    # Get calendar URL from args or config
    calendar_url = args.calendar_url
    project_name = args.project
    
    # Set date range (default to next 30 days)
    start_date = datetime.now() - timedelta(days=30)
    end_date = datetime.now() + timedelta(days=30)
    
    print(f"Fetching calendar events from {calendar_url}...")
    try:
        calendar_events = fetch_calendar_events(calendar_url, start_date, end_date)
    except Exception as e:
        print(f"Error fetching calendar events: {str(e)}")
        return
    
    print(f"Found {len(calendar_events)} calendar events")
    
    # Fetch tasks from OmniFocus
    print("Fetching tasks from OmniFocus...")
    tasks = apple_script_client.fetch_tasks(project_name=project_name)
    
    if not tasks:
        print(f"No tasks found in project '{project_name}' to check against calendar.")
        return
    
    # Sync tasks with calendar events
    print("Analyzing task reality status...")
    reality_status = sync_with_calendar(tasks, calendar_events)
    
    # Print results
    print("\n--- Task Reality Check ---")
    real_tasks_count = 0
    unreal_tasks_count = 0
    for task_id, is_real in reality_status.items():
        task_name = next((t.name for t in tasks if t.id == task_id), "Unknown Task")
        status = "REAL (matches calendar event)" if is_real else "NOT REAL (no matching calendar event)"
        print(f"- {task_name} (ID: {task_id}): {status}")
        if is_real:
            real_tasks_count +=1
        else:
            unreal_tasks_count += 1
    print(f"\nSummary: {real_tasks_count} real tasks, {unreal_tasks_count} unreal tasks.")

def escape_applescript_string_local(s: Optional[str]) -> str:
    if not s: return ""
    return s.replace('\\', '\\\\').replace('"', '\\"')

def parse_and_format_datetime_for_applescript(date_str_input: Optional[str]) -> Optional[str]:
    if not date_str_input: return None
    dt_obj = None
    if _parse_date_string_imported:
        try:
            # Assuming shared_parse_date_string returns datetime or None
            parsed_val = shared_parse_date_string(date_str_input)
            if isinstance(parsed_val, datetime):
                dt_obj = parsed_val
            elif isinstance(parsed_val, str): # If it returned string, it means it couldn't parse
                print(f"Warning: Shared date parser returned string for '{date_str_input}'. Date may not be set correctly.")
                return date_str_input # Pass as is for AppleScript to try
            # If None, dt_obj remains None
        except Exception as e_parse:
            print(f"Warning: Error using shared_parse_date_string for '{date_str_input}': {e_parse}. Falling back.")
            # Fallback to simpler local parsing if shared one fails or is not ideal
            pass # Will proceed to local parsing logic below if dt_obj is still None
    
    if not dt_obj: # Fallback or if shared parser not imported/failed
        try:
            if len(date_str_input) == 10: # YYYY-MM-DD
                dt_obj = datetime.datetime.strptime(date_str_input, "%Y-%m-%d")
            elif len(date_str_input) >= 16: # YYYY-MM-DD HH:MM
                dt_obj = datetime.datetime.strptime(date_str_input[:16], "%Y-%m-%d %H:%M")
        except ValueError:
            pass # dt_obj remains None

    if dt_obj:
        return dt_obj.strftime("%B %d, %Y %H:%M:%S") # e.g., "June 01, 2025 00:00:00"
    else:
        print(f"Warning: Date string '{date_str_input}' could not be parsed. Passing as is to AppleScript.")
        return date_str_input

def generate_add_calendar_event_applescript(
    title: str, 
    start_date_str: str, 
    end_date_str: str, 
    notes: Optional[str],
    calendar_name: Optional[str]
) -> str:
    escape_fn = shared_escape_applescript_string if _escape_applescript_string_imported else escape_applescript_string_local
    
    s_title = escape_fn(title)
    s_notes = escape_fn(notes)
    s_calendar_name = escape_fn(calendar_name)

    formatted_start_date = parse_and_format_datetime_for_applescript(start_date_str) or start_date_str
    formatted_end_date = parse_and_format_datetime_for_applescript(end_date_str) or end_date_str

    script_parts = [
        'tell application "Calendar"',
    ]

    target_calendar_line = "set targetCalendar to first calendar whose writable is true" 
    if s_calendar_name:
        target_calendar_line = f'set targetCalendar to first calendar whose name is "{s_calendar_name}"'
    
    # Pre-evaluate the name for the error message
    display_calendar_name_for_error = s_calendar_name or "(default writable)"

    script_parts.extend([
        '    try',
        f'        {target_calendar_line}',
        '    on error',
        f"        return \"Error: Calendar '{display_calendar_name_for_error}' not found.\"", # Use pre-evaluated name
        '    end try',
        '    tell targetCalendar',
        f'        make new event with properties {{summary:"{s_title}", start date:date "{formatted_start_date}", end date:date "{formatted_end_date}", description:"{s_notes}"}}',
        '    end tell',
        f"    return \"Event '{s_title}' created successfully.\""
    ])
    script_parts.append('end tell')
    return "\n".join(script_parts)

def handle_add_calendar_event(args):
    applescript_command = generate_add_calendar_event_applescript(
        args.title,
        args.start_date,
        args.end_date,
        args.notes,
        args.calendar_name
    )
    print("\nGenerated AppleScript for add-calendar-event (for review):")
    print("------------------------------------")
    print(applescript_command)
    print("------------------------------------\n")

    # Standard AppleScript execution logic (using temp file for osascript)
    # Avoiding specific execute_omnifocus_applescript name here
    _execute_applescript_fn = None
    try:
        from ..omnifocus_api.apple_script_client import execute_applescript as generic_execute_applescript
        _execute_applescript_fn = generic_execute_applescript
        print("Info: Using 'execute_applescript' from apple_script_client.")
    except ImportError:
        print("Info: 'execute_applescript' not found. Using direct 'osascript' call.")

    try:
        if _execute_applescript_fn:
            result = _execute_applescript_fn(applescript_command)
        else:
            tmp_file_path = None
            try:
                with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.applescript') as tmp_script_file:
                    tmp_script_file.write(applescript_command)
                    tmp_file_path = tmp_script_file.name
                process = subprocess.run(["osascript", tmp_file_path], capture_output=True, text=True, check=False)
                if process.returncode == 0:
                    result = process.stdout.strip()
                else:
                    result = f"Error: osascript failed. STDERR: {process.stderr.strip()}"
            finally:
                if tmp_file_path and os.path.exists(tmp_file_path):
                    os.remove(tmp_file_path)
        
        print(f"Apple Calendar AppleScript execution result:")
        print(result)

    except Exception as e:
        print(f"An unexpected error occurred during AppleScript execution: {e}") 