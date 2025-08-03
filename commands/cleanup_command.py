import sys
import os
import json
from typing import List, Dict, Optional
from enum import Enum
from ..omnifocus_api.apple_script_client import (
    fetch_inbox_tasks, fetch_flagged_tasks, fetch_overdue_tasks, 
    move_task_to_project, fetch_project_names, set_task_name, 
    set_task_note, complete_task, delete_task, unflag_task, fetch_subtasks,
    fetch_adjacent_tasks_context
)
from ..omnifocus_api.data_models import OmniFocusTask
from datetime import datetime, timedelta
from ..ai_integration.utils.prompt_utils import confirm_action
import re
import difflib
import subprocess
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from ..ai_integration.llama3_ollama_client import query_llama3

def clear_terminal():
    """Clear the terminal screen."""
    os.system('cls' if os.name == 'nt' else 'clear')

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

def display_task_info(task, subtasks, adjacent_context, status_list):
    """Display task information in a clean, formatted way."""
    print("\n" + "=" * 60)
    print(f"📋 TASK: {task['name']}")
    print(f"🆔 ID: {task['id']}")
    
    # Status indicators
    status_icons = []
    if task.get("due_date"):
        status_icons.append(f"📅 Due: {task['due_date']}")
    if task.get("flagged"):
        status_icons.append("🚩 Flagged")
    if task.get("completed"):
        status_icons.append("✅ Completed")
    if task.get("project"):
        status_icons.append(f"📁 Project: {task.get('project')}")
    
    if status_icons:
        print("   " + " | ".join(status_icons))
    
    # Notes (truncated)
    if task.get("note"):
        note_preview = task.get("note")[:80] + "..." if len(task.get("note")) > 80 else task.get("note")
        print(f"📝 Note: {note_preview}")
    
    # Subtasks
    if subtasks:
        print(f"\n📋 Subtasks ({len(subtasks)}):")
        for subtask in subtasks:
            print(f"   • {subtask['name']}")
    
    # Adjacent context for inbox tasks
    if adjacent_context and adjacent_context.get("adjacent_tasks"):
        print(f"\n🔗 Context (adjacent tasks):")
        for adj_task in adjacent_context["adjacent_tasks"][:3]:  # Limit to 3
            if adj_task["is_target"]:
                print(f"   🎯 {adj_task['name']} (current)")
            else:
                project_info = f" → {adj_task['project_context']}" if adj_task['project_context'] != "INBOX" else ""
                print(f"   📋 {adj_task['name']}{project_info}")
    
    # Status summary
    if status_list:
        print(f"\n🏷️  Status: {', '.join(status_list)}")

def get_auto_routing_project(task, available_projects):
    """Get automatic project routing based on task content."""
    task_name = task.get('name', '').lower()
    task_note = task.get('note', '').lower()
    
    # Family Member 1 related tasks
    if any(phrase in task_name or phrase in task_note for phrase in ['family member 1', 'member 1']):
        # Look for existing Family Member 1 project
        for proj in available_projects:
            if 'family member 1' in proj.lower():
                return proj
        # If no Family Member 1 project exists, create one
        return "[NEW] Family Member 1"
    
    # Company/Work related tasks
    if any(word in task_name or word in task_note for word in ['company', 'work', 'job', 'career', 'meeting']):
        for proj in available_projects:
            if 'work' in proj.lower() or 'career' in proj.lower():
                return proj
        # If no work project exists, create one
        return "[NEW] Work"
    
    # Work/Gartner related tasks
    if any(word in task_name or word in task_note for word in ['work', 'job', 'career', 'meeting']):
        for proj in available_projects:
            if 'work' in proj.lower():
                return proj
    
    # Family Member 5 related tasks
    if any(word in task_name or word in task_note for word in ['family member 5', 'member 5']):
        for proj in available_projects:
            if 'family member 5' in proj.lower():
                return proj
    
    # Family Member 5 related tasks
    if any(word in task_name or word in task_note for word in ['family member 5', 'basketball', 'healing']):
        for proj in available_projects:
            if 'family member 5' in proj.lower():
                return proj
    
    # Family/Parenting related tasks
    if any(word in task_name or word in task_note for word in ['parent', 'child', 'family', 'parenting']):
        for proj in available_projects:
            if any(family_word in proj.lower() for family_word in ['family', 'parent', 'child']):
                return proj
        return "[NEW] Family"
    
    return None

def get_fallback_suggestions(task, available_projects):
    """Provide fallback suggestions when LLM fails."""
    task_name = task.get('name', '').lower()
    task_note = task.get('note', '').lower()
    
    # Simple keyword matching for common project types
    suggestions = []
    
    # Finance-related keywords
    if any(word in task_name or word in task_note for word in ['finance', 'money', 'bank', 'credit', 'bill', 'payment', 'account']):
        for proj in available_projects:
            if any(word in proj.lower() for word in ['finance', 'wealth', 'money']):
                suggestions.append({
                    'project': proj,
                    'confidence': 0.8,
                    'justification': 'Finance-related task'
                })
                break
    
    # Work-related keywords
    if any(word in task_name or word in task_note for word in ['work', 'job', 'career', 'gartner', 'meeting', 'project']):
        for proj in available_projects:
            if any(word in proj.lower() for word in ['gartner', 'work', 'career']):
                suggestions.append({
                    'project': proj,
                    'confidence': 0.8,
                    'justification': 'Work-related task'
                })
                break
    
    # Family-related keywords
    if any(word in task_name or word in task_note for word in ['family', 'kids', 'children']):
        # Check for specific family member projects first
        family_members = ['family member 1', 'family member 2', 'family member 3', 'family member 4', 'family member 5']
        for member in family_members:
            if member in task_name or member in task_note:
                for proj in available_projects:
                    if member.lower() in proj.lower():
                        suggestions.append({
                            'project': proj,
                            'confidence': 0.9,
                            'justification': f'{member.title()}-specific task'
                        })
                        break
        
        # If no specific member project found, look for general family projects
        if not suggestions:
            for proj in available_projects:
                if any(word in proj.lower() for word in ['family', 'fun', 'coordination']):
                    suggestions.append({
                        'project': proj,
                        'confidence': 0.8,
                        'justification': 'Family-related task'
                    })
                    break
    
    # House-related keywords
    if any(word in task_name or word in task_note for word in ['house', 'home', 'repair', 'maintenance', 'clean', 'organize']):
        for proj in available_projects:
            if any(word in proj.lower() for word in ['house', 'home', 'project']):
                suggestions.append({
                    'project': proj,
                    'confidence': 0.8,
                    'justification': 'House-related task'
                })
                break
    
    # Default to first few projects if no matches
    if not suggestions and available_projects:
        for i, proj in enumerate(available_projects[:3]):
            suggestions.append({
                'project': proj,
                'confidence': 0.5,
                'justification': 'Default suggestion'
            })
    
    return suggestions

def get_llm_suggestions(task, available_projects):
    """Get LLM suggestions for project assignment with better error handling."""
    try:
        # Simplified prompt for faster response
        project_list_str = ', '.join(f'"{p}"' for p in available_projects)
        prompt = (
            f"Task: {task.get('name', '')}\n"
            f"Note: {task.get('note', '')}\n"
            f"Projects: [{project_list_str}]\n"
            f"Suggest 2-3 best project matches from the list. JSON format: [{{'project': 'name', 'confidence': 0.9, 'justification': 'brief reason'}}]"
        )
        
        llm_response = query_llama3(prompt)
        json_str = extract_json_from_response(llm_response)
        suggestions = json.loads(json_str)
        
        # Ensure all suggestions have required fields with defaults
        for suggestion in suggestions:
            suggestion.setdefault('justification', 'No justification provided')
            suggestion.setdefault('confidence', 0.5)
        
        return suggestions, None
        
    except Exception as e:
        return [], f"LLM suggestion error: {str(e)}"

def show_detailed_context(task, subtasks, adjacent_context, status_list):
    """Show detailed context for a task."""
    clear_terminal()
    print(f"🔍 DETAILED CONTEXT")
    print("=" * 50)
    print(f"📋 Task: {task['name']}")
    print(f"🆔 ID: {task['id']}")
    
    # Full task details
    if task.get("due_date"):
        print(f"📅 Due: {task['due_date']}")
    if task.get("flagged"):
        print("🚩 Flagged")
    if task.get("completed"):
        print("✅ Completed")
    if task.get("project"):
        print(f"📁 Project: {task.get('project')}")
    if task.get("note"):
        print(f"\n📝 Full Note:\n{task.get('note')}")
    
    # All subtasks
    if subtasks:
        print(f"\n📋 All Subtasks ({len(subtasks)}):")
        for i, subtask in enumerate(subtasks, 1):
            print(f"   {i}. {subtask['name']} (ID: {subtask['id']})")
            if subtask.get('note'):
                print(f"      Note: {subtask['note'][:60]}...")
    
    # Full adjacent context
    if adjacent_context and adjacent_context.get("adjacent_tasks"):
        print(f"\n🔗 Full Context (all adjacent tasks):")
        for adj_task in adjacent_context["adjacent_tasks"]:
            if adj_task["is_target"]:
                print(f"   🎯 {adj_task['name']} (CURRENT)")
            else:
                project_info = f" → {adj_task['project_context']}" if adj_task['project_context'] != "INBOX" else " (INBOX)"
                print(f"   📋 {adj_task['name']}{project_info}")
    
    # Status details
    if status_list:
        print(f"\n🏷️  Status: {', '.join(status_list)}")
    
    input("\nPress Enter to continue...")

def display_suggestions(suggestions, available_projects):
    """Display LLM suggestions in a clean format."""
    if not suggestions:
        return
    
    print(f"\n🤖 AI Suggestions:")
    for idx, suggestion in enumerate(suggestions, 1):
        confidence = suggestion.get('confidence', 0.5)
        confidence_bar = "█" * int(confidence * 10) + "░" * (10 - int(confidence * 10))
        print(f"   {idx}. {suggestion['project']} [{confidence_bar}] {confidence:.1f}")
        print(f"      💡 {suggestion['justification']}")
        
        # Show fuzzy matches if project doesn't exist
        if suggestion['project'] not in available_projects:
            close_matches = difflib.get_close_matches(suggestion['project'], available_projects, n=2, cutoff=0.6)
            if close_matches:
                print(f"      🔍 Similar: {', '.join(close_matches)}")

def get_action_choice(task_id, suggestions, available_projects, inbox_ids):
    """Get user action choice with simplified options."""
    print(f"\n🎯 Actions:")
    
    # Always show core actions
    print(f"   c - Complete")
    print(f"   d - Delete")
    print(f"   s - Skip")
    print(f"   q - Quit")
    
    # Show inbox-specific actions (most common)
    if task_id in inbox_ids:
        print(f"   m - Move to project")
        print(f"   f - Family routing")
    
    # Get user choice with minimal validation
    valid_options = ['c', 'd', 's', 'q']
    if task_id in inbox_ids:
        valid_options.extend(['m', 'f'])
    
    return get_user_input("Action: ", valid_options)

def handle_move_action(task, suggestions, available_projects):
    """Handle the move action with streamlined UI."""
    if suggestions:
        # Show suggestions in a compact format
        print(f"\n🤖 AI Suggestions:")
        for idx, suggestion in enumerate(suggestions, 1):
            confidence = suggestion.get('confidence', 0.5)
            print(f"   {idx} - {suggestion['project']} ({confidence:.1f})")
        
        print(f"\n📁 Quick Options:")
        print(f"   s - Skip")
        print(f"   n - Create new project")
        print(f"   a - Show all projects")
        
        # Get selection with minimal typing
        valid_options = ['s', 'n', 'a'] + [str(i) for i in range(1, len(suggestions) + 1)]
        choice = get_user_input("Select: ", valid_options)
        
        if choice == 's':
            return False, None
        elif choice == 'n':
            new_project = input("New project name: ").strip()
            if new_project:
                return True, f"[NEW] {new_project}"
            else:
                print("❌ Project name cannot be empty")
                return False, None
        elif choice == 'a':
            # Show all projects
            return handle_comprehensive_project_selection(available_projects)
        else:
            idx = int(choice) - 1
            selected_project = suggestions[idx]['project']
            return True, selected_project
    else:
        # No suggestions, show all projects for better selection
        return handle_comprehensive_project_selection(available_projects)

def handle_simple_project_selection(available_projects):
    """Handle simple project selection with top 10 most relevant projects."""
    # Define priority projects that are most commonly used
    priority_projects = [
        'Daily Routines', 'Weekly Tasks', 'Monthly Tasks', 'Quarterly Tasks',
        'Finance', 'Finance Admin', 'Family Coordination', 'Reference Materials',
        'Ad-Hoc Tasks', 'House Projects'
    ]
    
    # Get top 10 projects (priority first, then others)
    top_projects = []
    for proj in priority_projects:
        if proj in available_projects and proj not in top_projects:
            top_projects.append(proj)
    
    # Add other projects to fill up to 10
    for proj in available_projects:
        if proj not in top_projects and len(top_projects) < 10:
            top_projects.append(proj)
    
    print(f"\n📁 Top Projects:")
    for i, proj in enumerate(top_projects, 1):
        print(f"   {i} - {proj}")
    
    print(f"\n📁 Quick Options:")
    print(f"   s - Skip")
    print(f"   n - Create new project")
    print(f"   ... or type number/name")
    
    project_input = input("Select: ").strip()
    
    # Check if it's a number (quick selection)
    if project_input.isdigit():
        idx = int(project_input) - 1
        if 0 <= idx < len(top_projects):
            return True, top_projects[idx]
        else:
            print("❌ Invalid number")
            return False, None
    
    # Check if it's a special command
    if project_input.lower() == 's':
        return False, None
    elif project_input.lower() == 'n':
        new_project = input("New project name: ").strip()
        if new_project:
            return True, f"[NEW] {new_project}"
        else:
            print("❌ Project name cannot be empty")
            return False, None
    
    # Check if it's a full project name
    if project_input in available_projects:
        return True, project_input
    else:
        print(f"❌ Project not found")
        return False, None

def handle_comprehensive_project_selection(available_projects):
    """Handle comprehensive project selection with simple alphabetical sorting."""
    # Sort projects alphabetically for consistent ordering
    sorted_projects = sorted(available_projects)
    
    print(f"\n📁 All Projects:")
    for i, proj in enumerate(sorted_projects, 1):
        print(f"   {i:2d} - {proj}")
    
    print(f"\n📁 Quick Options:")
    print(f"   s - Skip")
    print(f"   n - Create new project")
    print(f"   ... or type number/name")
    
    project_input = input("Select: ").strip()
    
    # Check if it's a number (quick selection)
    if project_input.isdigit():
        idx = int(project_input) - 1
        if 0 <= idx < len(sorted_projects):
            return True, sorted_projects[idx]
        else:
            print("❌ Invalid number")
            return False, None
    
    # Check if it's a special command
    if project_input.lower() == 's':
        return False, None
    elif project_input.lower() == 'n':
        new_project = input("New project name: ").strip()
        if new_project:
            return True, f"[NEW] {new_project}"
        else:
            print("❌ Project name cannot be empty")
            return False, None
    
    # Check if it's a full project name
    if project_input in available_projects:
        return True, project_input
    else:
        print(f"❌ Project not found")
        return False, None

def handle_family_routing(task, available_projects):
    """Handle quick family member routing."""
    print(f"\n👨‍👩‍👧‍👦 Family Routing:")
    print(f"   1 - Family Member 1")
    print(f"   2 - Family Member 2")
    print(f"   3 - Family Member 3")
    print(f"   4 - Family Member 4")
    print(f"   5 - Family Member 5")
    print(f"   s - Skip")
    
    choice = get_user_input("Select family member: ", ['1', '2', '3', '4', '5', 's'])
    
    if choice == 's':
        return None
    
    family_members = ['Family Member 1', 'Family Member 2', 'Family Member 3', 'Family Member 4', 'Family Member 5']
    selected_member = family_members[int(choice) - 1]
    
    # Look for existing family member projects
    for proj in available_projects:
        if selected_member.lower() in proj.lower():
            return proj
    
    # If no existing project, create a new one
    return f"[NEW] {selected_member}"

def handle_cleanup(args):
    """
    Interactive cleanup of overdue, flagged, and inbox items with improved UI.
    """
    clear_terminal()
    print("🧹 OmniFocus Cleanup - Improved Interface")
    print("=" * 50)
    
    mode = args.mode
    batch_size = args.batch
    
    # Initialize task lists
    inbox_tasks = []
    flagged_tasks = []
    overdue_tasks = []
    
    if mode == "inbox":
        print("\n📥 Cleaning up Inbox items...")
        inbox_tasks = [t for t in fetch_inbox_tasks() if not t.get("completed")]
    elif mode == "flagged":
        print("\n🚩 Cleaning up Flagged items...")
        flagged_tasks = [t for t in fetch_flagged_tasks() if not t.get("completed")]
    elif mode == "overdue":
        print("\n⏰ Cleaning up Overdue items...")
        overdue_tasks = [t for t in fetch_overdue_tasks() if not t.get("completed")]
    else:
        print("\n🔍 Cleaning up all problematic items...")
        inbox_tasks = [t for t in fetch_inbox_tasks() if not t.get("completed")]
        flagged_tasks = [t for t in fetch_flagged_tasks() if not t.get("completed")]
        overdue_tasks = [t for t in fetch_overdue_tasks() if not t.get("completed")]
    
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
        print("✅ No tasks found to clean up!")
        return
    
    print(f"\n📊 Found {len(tasks)} tasks to review.")
    
    # Fetch available project names once at the start
    available_projects = fetch_project_names()
    
    processed = 0
    evernote_queue = []  # Tasks to be moved to Evernote
    
    for task in tasks:
        # Clear terminal for each new task
        clear_terminal()
        
        # Show progress
        task_name_preview = task['name'][:40] + "..." if len(task['name']) > 40 else task['name']
        print(f"🧹 OmniFocus Cleanup - Task {processed + 1} of {len(tasks)}")
        print(f"📋 Current: {task_name_preview}")
        print("=" * 50)
        
        # Get task details
        subtasks = fetch_subtasks(task["id"])
        
        # Display task information (without context or status)
        display_task_info(task, subtasks, None, [])
        
        # Get LLM suggestions for inbox tasks
        suggestions = []
        llm_error = None
        if task["id"] in inbox_ids:
            # Check for automatic routing first
            auto_project = get_auto_routing_project(task, available_projects)
            if auto_project:
                suggestions = [{
                    'project': auto_project,
                    'confidence': 0.95,
                    'justification': 'Auto-routed based on content'
                }]
                print(f"\n🤖 Auto-routed to: {auto_project}")
            else:
                # Check if AI suggestions are disabled
                if os.getenv('OF_DISABLE_AI_SUGGESTIONS'):
                    # Skip AI suggestions, will show all projects in move action
                    pass
                else:
                    suggestions, llm_error = get_llm_suggestions(task, available_projects)
                    if llm_error:
                        print(f"\n⚠️  {llm_error}")
                        # Provide fallback suggestions based on task name
                        suggestions = get_fallback_suggestions(task, available_projects)
        
        # Get user action with default suggestion for inbox items
        if task["id"] in inbox_ids and suggestions:
            print(f"\n💡 Suggested: 'm' (Move to project with AI suggestions)")
        
        action = get_action_choice(task["id"], suggestions, available_projects, inbox_ids)
        
        if action == 'q':
            print("\n👋 Cleanup stopped by user.")
            break
            
        elif action == 'e':
            notebook = input("📓 Enter Evernote notebook name (or press Enter for default): ").strip() or "Reference Material"
            tags = input("🏷️  Enter tags (comma-separated, or press Enter for none): ").strip()
            
            # Queue the task and its subtasks for Evernote export
            evernote_queue.append({
                'task': task,
                'subtasks': subtasks,
                'notebook': notebook,
                'tags': [tag.strip() for tag in tags.split(',')] if tags else []
            })
            
            # Mark task as complete in OmniFocus after queuing for Evernote
            if complete_tasks_with_subtasks(task["id"], subtasks):
                print("✅ Task queued for Evernote export and marked complete")
            else:
                print("❌ Failed to mark all tasks complete")
            
        elif action == 'c':
            # Mark the task as completed
            if complete_task(task["id"]):
                print("✅ Task marked as completed")
            else:
                print("❌ Failed to mark task as completed")
                
        elif action == 'd':
            # Delete subtasks first
            subtask_success = True
            for subtask in subtasks:
                if not delete_task(subtask['id']):
                    print(f"❌ Failed to delete subtask: {subtask['name']}")
                    subtask_success = False
            
            # Then delete main task
            if delete_task(task["id"]):
                if subtask_success:
                    print("✅ Task and all subtasks deleted")
                else:
                    print("⚠️  Main task deleted but some subtasks failed")
            else:
                print("❌ Failed to delete main task")
                
        elif action == 'u':
            if unflag_task(task["id"]):
                print("✅ Flag removed")
                # Unflag subtasks as well
                for subtask in subtasks:
                    if not unflag_task(subtask['id']):
                        print(f"⚠️  Failed to unflag subtask: {subtask['name']}")
            else:
                print("❌ Failed to remove flag")
                
        elif action == 'm':
            should_move, project_name = handle_move_action(task, suggestions, available_projects)
            if should_move and project_name:
                if move_task_to_project(task["id"], project_name):
                    print(f"✅ Moved to project: {project_name}")
                else:
                    print(f"❌ Failed to move to project: {project_name}")
            elif not should_move:
                print("⏭️  Skipped moving task")
            else:
                print("❌ Invalid project name")
                
        elif action == 'f':
            family_project = handle_family_routing(task, available_projects)
            if family_project:
                if move_task_to_project(task["id"], family_project):
                    print(f"✅ Moved to family project: {family_project}")
                else:
                    print(f"❌ Failed to move to family project: {family_project}")
            else:
                print("⏭️  Skipped family routing")
                
        elif action == 't':
            # Set due date to today
            from datetime import datetime
            today = datetime.now().strftime("%A, %B %d, %Y at %I:%M:%S %p")
            # Note: This would need a set_due_date function in the API
            print("📅 Due date set to today (functionality to be implemented)")
            
        elif action == 'w':
            # Set due date to end of week
            from datetime import datetime, timedelta
            today = datetime.now()
            end_of_week = today + timedelta(days=(6 - today.weekday()))
            end_of_week_str = end_of_week.strftime("%A, %B %d, %Y at %I:%M:%S %p")
            # Note: This would need a set_due_date function in the API
            print(f"📅 Due date set to end of week: {end_of_week_str} (functionality to be implemented)")
            
        elif action == 'x':
            show_detailed_context(task, subtasks, adjacent_context, status_list)
            continue  # Don't increment processed, show the same task again
        
        elif action == 's':
            print("⏭️  Skipped task")
        
        processed += 1
    
    # Handle Evernote export queue
    if evernote_queue:
        print(f"\n📓 Evernote Export Queue ({len(evernote_queue)} tasks):")
        for item in evernote_queue:
            print(f"   • {item['task']['name']} → {item['notebook']}")
        print("   (Evernote export functionality to be implemented)")
    
    print(f"\n🎉 Cleanup complete! Processed {processed} tasks.")

def extract_json_from_response(response: str):
    """Extract JSON from LLM response with better error handling."""
    # Clean up the response
    response = response.strip()
    
    # Try to find JSON array in the response
    json_match = re.search(r'\[.*\]', response, re.DOTALL)
    if json_match:
        try:
            # Validate the JSON
            json.loads(json_match.group(0))
            return json_match.group(0)
        except json.JSONDecodeError:
            pass
    
    # If no valid JSON array found, try to extract individual JSON objects
    json_objects = re.findall(r'\{[^}]*\}', response)
    if json_objects:
        try:
            # Try to combine them into a valid array
            combined = '[' + ','.join(json_objects) + ']'
            json.loads(combined)
            return combined
        except json.JSONDecodeError:
            pass
    
    # If still no valid JSON found, return empty array
    return '[]' 