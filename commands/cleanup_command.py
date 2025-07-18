import sys
import os
import json
from typing import List, Dict, Optional
from enum import Enum
from omnifocus_api.apple_script_client import (
    fetch_inbox_tasks, fetch_flagged_tasks, fetch_overdue_tasks, 
    move_task_to_project, fetch_project_names, set_task_name, 
    set_task_note, complete_task, delete_task, unflag_task, fetch_subtasks,
    fetch_adjacent_tasks_context
)
from omnifocus_api.data_models import OmniFocusTask
from datetime import datetime, timedelta
from ai_integration.utils.prompt_utils import confirm_action
import re
import difflib
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from ai_integration.llama3_ollama_client import query_llama3

def get_user_input(prompt: str, valid_options: list) -> str:
    """Get user input with validation."""
    while True:
        response = input(prompt).strip().lower()
        if response in valid_options:
            return response
        print(f"Please enter one of: {', '.join(valid_options)}")

def complete_tasks_with_subtasks(task_id: str, subtasks: List[OmniFocusTask]) -> bool:
    """Helper function to complete a task and its subtasks."""
    # First complete all subtasks
    subtask_success = True
    for subtask in subtasks:
        if not complete_task(subtask.id):
            print(f"✗ Failed to complete subtask: {subtask.name}")
            subtask_success = False
    
    # Then complete the main task
    main_success = complete_task(task_id)
    if not main_success:
        print(f"✗ Failed to complete main task (ID: {task_id})")
    
    return main_success and subtask_success

def is_problematic(task):
    from datetime import datetime
    now = datetime.now()
    # Parse due date if present
    due = None
    if task.get("due_date"):
        try:
            due = datetime.strptime(task["due_date"], "%A, %B %d, %Y at %I:%M:%S %p")
        except Exception:
            due = None
    overdue = due and due < now
    flagged = task.get("flagged", False)
    inbox = task.get("status", "").upper() == "INBOX"
    return overdue or flagged or inbox

def handle_cleanup(args):
    """
    Interactive cleanup of overdue, flagged, and inbox items, now with LLM suggestions for inbox tasks.
    """
    print("Cleanup and task completion are now handled via OmniFocus-MCP. Please use that tool for these operations.")
    mode = args.mode
    batch_size = args.batch
    
    # Initialize task lists
    inbox_tasks = []
    flagged_tasks = []
    overdue_tasks = []
    
    if mode == "inbox":
        print("\nCleaning up Inbox items...")
        inbox_tasks = fetch_inbox_tasks()
    elif mode == "flagged":
        print("\nCleaning up Flagged items...")
        flagged_tasks = fetch_flagged_tasks()
    elif mode == "overdue":
        print("\nCleaning up Overdue items...")
        overdue_tasks = fetch_overdue_tasks()
    else:
        print("\nCleaning up all problematic items...")
        inbox_tasks = fetch_inbox_tasks()
        flagged_tasks = fetch_flagged_tasks()
        overdue_tasks = fetch_overdue_tasks()
    
    # Combine and deduplicate tasks
    seen_ids = set()
    tasks = []
    for task in (inbox_tasks if 'inbox_tasks' in locals() else []) + \
                (flagged_tasks if 'flagged_tasks' in locals() else []) + \
                (overdue_tasks if 'overdue_tasks' in locals() else []):
        if task["id"] not in seen_ids:
            seen_ids.add(task["id"])
            tasks.append(task)
    
    # Create sets of IDs for efficient lookup
    inbox_ids = {t["id"] for t in inbox_tasks}
    flagged_ids = {t["id"] for t in flagged_tasks}
    overdue_ids = {t["id"] for t in overdue_tasks}
    
    if not tasks:
        print("No tasks found to clean up!")
        return
    
    print(f"\nFound {len(tasks)} tasks to review.")
    print("\nFor each task, you can:")
    print("(c)omplete - Mark the task as done")
    print("(d)elete - Remove the task")
    print("(u)nflag - Remove the flag")
    print("(m)ove - Move to a project")
    print("(e)vernote - Move to Evernote as reference")
    print("(t)oday - Set due date to today")
    print("(w)eek - Set due date to end of week")
    print("(s)kip - Keep as is")
    print("(q)uit - Stop cleanup")
    print("\nStarting review...")
    
    processed = 0
    evernote_queue = []  # Tasks to be moved to Evernote
    
    # Fetch available project names once at the start
    available_projects = fetch_project_names()
    
    for task in tasks:
        if batch_size and processed >= batch_size:
            if get_user_input("\nBatch complete. Continue with next batch? (y/n): ", ['y', 'n']) == 'n':
                break
            processed = 0
            
        print("\n" + "=" * 50)
        print(f"Task: {task['name']}")
        print(f"ID: {task['id']}")  # Add this line to help with debugging
        if task.get("due_date"):
            print(f"Due: {task['due_date']}")
        if task.get("flagged"):
            print("Flagged!")
        if task.get("completed"):
            print("Completed!")
        if task.get("project"):
            print(f"Project: {task.get('project')}")
        if task.get("note"):
            print(f"Note: {task.get('note')[:100]}...")
            
                # Get and display subtasks if any
        subtasks = fetch_subtasks(task["id"])
        if subtasks:
            print("\nSubtasks:")
            for subtask in subtasks:
                print(f"  - {subtask['name']} (ID: {subtask['id']})")  # Add subtask IDs for debugging
        
        # Get and display adjacent tasks context for inbox tasks
        if task["id"] in inbox_ids:
            adjacent_context = fetch_adjacent_tasks_context(task["id"], context_size=2)
            if adjacent_context["adjacent_tasks"]:
                print("\n📅 Temporal Context (Adjacent Tasks):")
                for adj_task in adjacent_context["adjacent_tasks"]:
                    if adj_task["is_target"]:
                        print(f"  🎯 TARGET: {adj_task['name']} (INBOX)")
                    else:
                        project_info = f" → {adj_task['project_context']}" if adj_task['project_context'] != "INBOX" else " (INBOX)"
                        print(f"  📋 {adj_task['name']}{project_info}")
                
                # Analyze project patterns
                non_inbox_projects = [t["project_context"] for t in adjacent_context["adjacent_tasks"] 
                                    if not t["is_target"] and t["project_context"] != "INBOX"]
                if non_inbox_projects:
                    unique_projects = list(set(non_inbox_projects))
                    if len(unique_projects) == 1:
                        print(f"  💡 Context Hint: Adjacent tasks are in '{unique_projects[0]}' - consider this project")
                    else:
                        print(f"  💡 Context Hint: Adjacent tasks are in: {', '.join(unique_projects)}")
        
        status = []
        if task["id"] in inbox_ids:
            status.append("INBOX")
        if task["id"] in flagged_ids:
            status.append("FLAGGED")
        if task["id"] in overdue_ids:
            status.append("OVERDUE")
        print(f"Status: {', '.join(status)}")
        
        # --- LLM SUGGESTIONS FOR INBOX TASKS ---
        if task["id"] in inbox_ids:
            # Prepare a comma-separated list for the LLM prompt
            project_list_str = ', '.join(f'"{p}"' for p in available_projects)
            prompt = (
                f"You are an expert OmniFocus user. "
                f"Given the following task, suggest up to 3 project names (ranked by confidence) "
                f"and provide a short justification for each. "
                f"If you are unsure, include a 'Manual Review' option with justification.\n"
                f"Task Name: {task.get('name', '')}\n"
                f"Task Note: {task.get('note', '')}\n"
                f"Here are the available projects: [{project_list_str}]. Only suggest from these.\n"
                f"If none of the project names is an exact match, select the closest/most relevant project name from the list.\n"
                f"Respond with only a JSON array, no extra text, no markdown, no explanation. "
                f"Format: [{{'project': ..., 'confidence': ..., 'justification': ...}}, ...] "
                f"Every suggestion must include all three fields: project, confidence, and justification."
            )
            try:
                llm_response = query_llama3(prompt)
                json_str = extract_json_from_response(llm_response)
                suggestions = json.loads(json_str)
                # Ensure all suggestions have required fields with defaults
                for suggestion in suggestions:
                    suggestion.setdefault('justification', 'No justification provided')
            except Exception as e:
                print(f"[LLM Error] Could not get suggestions: {e}")
                print(f"[LLM Raw Response]: {llm_response}")
                suggestions = []
        else:
            suggestions = []
            
        action = get_user_input(
            "\nWhat would you like to do? (c/d/u/m/e/t/w/s/q): ",
            ['c', 'd', 'u', 'm', 'e', 't', 'w', 's', 'q']
        )
        
        if action == 'q':
            break
            
        elif action == 'e':
            notebook = input("Enter Evernote notebook name (or press Enter for default): ").strip() or "Reference Material"
            tags = input("Enter tags (comma-separated, or press Enter for none): ").strip()
            
            # Queue the task and its subtasks for Evernote export
            evernote_queue.append({
                'task': task,
                'subtasks': subtasks,
                'notebook': notebook,
                'tags': [tag.strip() for tag in tags.split(',')] if tags else []
            })
            
            # Mark task as complete in OmniFocus after queuing for Evernote
            if complete_tasks_with_subtasks(task["id"], subtasks):
                print("✓ Task queued for Evernote export and marked complete")
            else:
                print("✗ Failed to mark all tasks complete")
            
        elif action == 'c':
            # Mark the task as completed
            if complete_task(task["id"]):
                print("✓ Task marked as completed")
            else:
                print("✗ Failed to mark task as completed")
                
        elif action == 'd':
            # Delete subtasks first
            subtask_success = True
            for subtask in subtasks:
                if not delete_task(subtask['id']):
                    print(f"✗ Failed to delete subtask: {subtask['name']}")
                    subtask_success = False
            
            # Then delete main task
            if delete_task(task["id"]):
                if subtask_success:
                    print("✓ Task and all subtasks deleted")
                else:
                    print("⚠ Main task deleted but some subtasks failed")
            else:
                print("✗ Failed to delete main task")
                
        elif action == 'u':
            if unflag_task(task["id"]):
                print("✓ Flag removed")
                # Unflag subtasks as well
                for subtask in subtasks:
                    if not unflag_task(subtask['id']):
                        print(f"⚠ Failed to unflag subtask: {subtask['name']}")
            else:
                print("✗ Failed to remove flag")
                
        elif action == 'm':
            if suggestions:
                print("LLM Project Suggestions:")
                menu_options = []
                for idx, suggestion in enumerate(suggestions, 1):
                    # Always show the suggestion, but if not an exact match, also show fuzzy matches
                    print(f"  {idx}. Project: {suggestion['project']} (Confidence: {suggestion['confidence']})")
                    print(f"     Justification: {suggestion['justification']}")
                    menu_options.append({'project': suggestion['project'], 'justification': suggestion['justification'], 'confidence': suggestion['confidence']})
                    if suggestion['project'] is not None and suggestion['project'] not in available_projects:
                        # Fuzzy match to suggest closest real project(s)
                        close_matches = difflib.get_close_matches(suggestion['project'], available_projects, n=3, cutoff=0.6)
                        for match in close_matches:
                            print(f"     (Closest match: {match})")
                            menu_options.append({'project': match, 'justification': f"Fuzzy match for '{suggestion['project']}'", 'confidence': suggestion['confidence']})
                print(f"  s. Skip")
                print(f"  m. Enter a different project name")
                # Build selection map
                selection_map = {str(i+1): opt for i, opt in enumerate(menu_options)}
                selection_map['s'] = 'skip'
                selection_map['m'] = 'manual'
                # Prompt user for selection
                while True:
                    sel = input(f"Select a project to move to [1-{len(menu_options)}, s, m]: ").strip()
                    if sel in selection_map:
                        break
                if selection_map[sel] == 'skip':
                    print("Task skipped.")
                    continue
                elif selection_map[sel] == 'manual':
                    project = input("Enter project name: ")
                    justification = "User entered project manually."
                else:
                    project = selection_map[sel]['project']
                    justification = selection_map[sel]['justification']
                # Move the task and append justification to note
                if move_task_to_project(task["id"], project):
                    # Append justification to note
                    note = task.get('note', '')
                    new_note = note + f"\n\n[LLM Categorization Justification]: {justification}"
                    try:
                        set_task_note(task["id"], new_note)
                    except Exception as e:
                        print(f"[Warning] Could not update note: {e}")
                    print(f"✓ Moved to project: {project} (Justification added to note)")
                else:
                    print("✗ Failed to move task")
            else:
                project = input("Enter project name: ")
                justification = "No LLM suggestion available."
                # No rephrase option if no LLM suggestion
                # Move the task and append justification to note
                if move_task_to_project(task["id"], project):
                    # Append justification to note
                    note = task.get('note', '')
                    new_note = note + f"\n\n[LLM Categorization Justification]: {justification}"
                    try:
                        set_task_note(task["id"], new_note)
                    except Exception as e:
                        print(f"[Warning] Could not update note: {e}")
                    print(f"✓ Moved to project: {project} (Justification added to note)")
                else:
                    print("✗ Failed to move task")
                
        elif action == 't':
            today = datetime.now().strftime("%Y-%m-%d")
            if apple_script_client.set_task_due_date(task["id"], today):
                print("✓ Due date set to today")
                # Set same due date for subtasks
                for subtask in subtasks:
                    if not apple_script_client.set_task_due_date(subtask.id, today):
                        print(f"⚠ Failed to set due date for subtask: {subtask.name}")
            else:
                print("✗ Failed to set due date")
                
        elif action == 'w':
            # Set due date to end of week (Sunday)
            today = datetime.now()
            days_until_sunday = 6 - today.weekday() if today.weekday() != 6 else 0
            end_of_week = today + timedelta(days=days_until_sunday)
            end_of_week = end_of_week.replace(hour=23, minute=59, second=0, microsecond=0)
            date_str = end_of_week.strftime("%Y-%m-%d %H:%M:%S")
            if apple_script_client.set_task_due_date(task["id"], date_str):
                print(f"Due date set to end of week: {date_str}")
                # Set same due date for subtasks
                for subtask in subtasks:
                    if not apple_script_client.set_task_due_date(subtask.id, date_str):
                        print(f"⚠ Failed to set due date for subtask: {subtask.name}")
            else:
                print("✗ Failed to set due date")
        
        # After any action that changes the task, re-fetch its status and skip if not problematic
        # (e.g., after (w)eek, (t)oday, (c)omplete, (u)nflag, etc.)
        # Example for (w)eek:
        if action in ["w", "t", "c", "u"]:
            # Re-fetch the task (simulate by updating the local dict if needed, or re-fetch from OmniFocus if possible)
            # For now, just re-check if it's still problematic
            if not is_problematic(task):
                print("Task is no longer problematic. Skipping to next.")
                continue
        
        processed += 1
    
    # Process Evernote queue if there are items
    if evernote_queue:
        print("\nProcessing Evernote exports...")
        for item in evernote_queue:
            task = item['task']
            content = f"# {task.name}\n\n"
            
            if task.note:
                content += f"## Notes\n{task.note}\n\n"
            
            if item['subtasks']:
                content += "## Subtasks\n"
                for subtask in item['subtasks']:
                    content += f"- {subtask.name}\n"
                    if subtask.note:
                        content += f"  > {subtask.note}\n"
            
            try:
                apple_script_client.export_to_evernote(
                    title=task.name,
                    content=content,
                    notebook=item['notebook'],
                    tags=item['tags']
                )
                print(f"✓ Exported '{task.name}' to Evernote")
            except Exception as e:
                print(f"✗ Failed to export '{task.name}' to Evernote: {str(e)}")
    
    print("\nCleanup session complete!")
    print(f"Processed {processed} tasks")
    if evernote_queue:
        print(f"Exported {len(evernote_queue)} items to Evernote") 

def extract_json_from_response(response: str):
    """
    Extract the first valid JSON array or object from a string, ignoring markdown/code fencing and extra text.
    """
    # Remove code fencing (``` and language hints)
    response = re.sub(r'```[a-zA-Z]*', '', response)
    response = response.replace('```', '')
    response = response.strip()
    # Try to find the first JSON array or object
    match = re.search(r'(\[.*?\]|\{.*?\})', response, re.DOTALL)
    if match:
        return match.group(1)
    return response  # fallback: return as-is 