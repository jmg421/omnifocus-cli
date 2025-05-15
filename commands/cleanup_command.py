import sys
from typing import List, Dict, Optional
from ..omnifocus_api import apple_script_client
from ..omnifocus_api.data_models import OmniFocusTask
from datetime import datetime, timedelta
from .prioritize_command import get_tasks_for_prioritization # Assuming same directory structure

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
        if not apple_script_client.complete_task(subtask.id):
            print(f"✗ Failed to complete subtask: {subtask.name}")
            subtask_success = False
    
    # Then complete the main task
    main_success = apple_script_client.complete_task(task_id)
    if not main_success:
        print(f"✗ Failed to complete main task (ID: {task_id})")
    
    return main_success and subtask_success

def handle_cleanup(args):
    """
    Interactive cleanup of overdue, flagged, and inbox items.
    """
    mode = args.mode
    batch_size = args.batch
    
    # Initialize task lists
    inbox_tasks = []
    flagged_tasks = []
    overdue_tasks = []
    
    if mode == "inbox":
        print("\nCleaning up Inbox items...")
        tasks = apple_script_client.fetch_inbox_tasks()
        inbox_tasks = tasks
    elif mode == "flagged":
        print("\nCleaning up Flagged items...")
        tasks = apple_script_client.fetch_flagged_tasks()
        flagged_tasks = tasks
    elif mode == "overdue":
        print("\nCleaning up Overdue items...")
        tasks = apple_script_client.fetch_overdue_tasks()
        overdue_tasks = tasks
    else:
        print("\nCleaning up all problematic items...")
        inbox_tasks = apple_script_client.fetch_inbox_tasks()
        flagged_tasks = apple_script_client.fetch_flagged_tasks()
        overdue_tasks = apple_script_client.fetch_overdue_tasks()
        
        # Combine and deduplicate tasks
        seen_ids = set()
        tasks = []
        for task in inbox_tasks + flagged_tasks + overdue_tasks:
            if task.id not in seen_ids:
                seen_ids.add(task.id)
                tasks.append(task)
    
    # Create sets of IDs for efficient lookup
    inbox_ids = {t.id for t in inbox_tasks}
    flagged_ids = {t.id for t in flagged_tasks}
    overdue_ids = {t.id for t in overdue_tasks}
    
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
    
    for task in tasks:
        if batch_size and processed >= batch_size:
            if get_user_input("\nBatch complete. Continue with next batch? (y/n): ", ['y', 'n']) == 'n':
                break
            processed = 0
            
        print("\n" + "=" * 50)
        print(f"Task: {task.name}")
        print(f"ID: {task.id}")  # Add this line to help with debugging
        if task.due_date:
            print(f"Due: {task.due_date}")
        if hasattr(task, 'project') and task.project:
            print(f"Project: {task.project}")
        if task.note:
            print(f"Note: {task.note[:100]}...")
            
        # Get and display subtasks if any
        subtasks = apple_script_client.fetch_subtasks(task.id) if hasattr(apple_script_client, 'fetch_subtasks') else []
        if subtasks:
            print("\nSubtasks:")
            for subtask in subtasks:
                print(f"  - {subtask.name} (ID: {subtask.id})")  # Add subtask IDs for debugging
            
        status = []
        if task.id in inbox_ids:
            status.append("INBOX")
        if task.id in flagged_ids:
            status.append("FLAGGED")
        if task.id in overdue_ids:
            status.append("OVERDUE")
        print(f"Status: {', '.join(status)}")
        
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
            if complete_tasks_with_subtasks(task.id, subtasks):
                print("✓ Task queued for Evernote export and marked complete")
            else:
                print("✗ Failed to mark all tasks complete")
            
        elif action == 'c':
            if complete_tasks_with_subtasks(task.id, subtasks):
                print("✓ Task and subtasks completed")
            else:
                print("✗ Failed to complete all tasks")
                
        elif action == 'd':
            # Delete subtasks first
            subtask_success = True
            for subtask in subtasks:
                if not apple_script_client.delete_task(subtask.id):
                    print(f"✗ Failed to delete subtask: {subtask.name}")
                    subtask_success = False
            
            # Then delete main task
            if apple_script_client.delete_task(task.id):
                if subtask_success:
                    print("✓ Task and all subtasks deleted")
                else:
                    print("⚠ Main task deleted but some subtasks failed")
            else:
                print("✗ Failed to delete main task")
                
        elif action == 'u':
            if apple_script_client.unflag_task(task.id):
                print("✓ Flag removed")
                # Unflag subtasks as well
                for subtask in subtasks:
                    if not apple_script_client.unflag_task(subtask.id):
                        print(f"⚠ Failed to unflag subtask: {subtask.name}")
            else:
                print("✗ Failed to remove flag")
                
        elif action == 'm':
            project = input("Enter project name: ")
            if apple_script_client.move_task_to_project(task.id, project):
                print(f"✓ Moved to project: {project}")
                # Move subtasks to the same project
                for subtask in subtasks:
                    if not apple_script_client.move_task_to_project(subtask.id, project):
                        print(f"⚠ Failed to move subtask: {subtask.name}")
            else:
                print("✗ Failed to move task")
                
        elif action == 't':
            today = datetime.now().strftime("%Y-%m-%d")
            if apple_script_client.set_task_due_date(task.id, today):
                print("✓ Due date set to today")
                # Set same due date for subtasks
                for subtask in subtasks:
                    if not apple_script_client.set_task_due_date(subtask.id, today):
                        print(f"⚠ Failed to set due date for subtask: {subtask.name}")
            else:
                print("✗ Failed to set due date")
                
        elif action == 'w':
            week_end = (datetime.now() + timedelta(days=(6 - datetime.now().weekday()))).strftime("%Y-%m-%d")
            if apple_script_client.set_task_due_date(task.id, week_end):
                print("✓ Due date set to end of week")
                # Set same due date for subtasks
                for subtask in subtasks:
                    if not apple_script_client.set_task_due_date(subtask.id, week_end):
                        print(f"⚠ Failed to set due date for subtask: {subtask.name}")
            else:
                print("✗ Failed to set due date")
        
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