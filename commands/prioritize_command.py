from ..omnifocus_api import apple_script_client
from ..omnifocus_api.data_models import OmniFocusTask
from ..ai_integration import ai_utils
from ..ai_integration.utils.format_utils import format_priority_recommendations
from ..ai_integration.utils.prompt_utils import get_prompt_template, save_prompt_template
import os
import re
from datetime import datetime
from typing import List, Optional

def get_tasks_for_prioritization(project_name: Optional[str], limit: Optional[int], finance_focus: bool) -> List[OmniFocusTask]:
    """Fetches tasks from OmniFocus based on project, limit, or finance focus."""
    tasks: List[OmniFocusTask] = []
    # Get tasks from OmniFocus
    if finance_focus:
        print("Getting finance-related tasks from OmniFocus...")
        # First try to get tasks from a Finance project if it exists
        tasks = apple_script_client.fetch_tasks(project_name="Finance")

        # If no Finance project, look for tasks with finance-related keywords
        if not tasks:
            print("No 'Finance' project found. Searching for finance-related tasks...")
            all_tasks = apple_script_client.fetch_tasks()
            finance_keywords = ["finance", "budget", "money", "expense", "investment",
                              "tax", "banking", "financial", "account"]

            tasks = []
            for task in all_tasks:
                # Check if task contains finance keywords
                task_text = f"{task.name} {task.note}".lower()
                if any(keyword in task_text for keyword in finance_keywords):
                    tasks.append(task)
    else:
        print(f"Getting tasks from OmniFocus{' for project: ' + project_name if project_name else ''}...")
        tasks = apple_script_client.fetch_tasks(project_name=project_name)

    # Limit the number of tasks if needed
    if limit and len(tasks) > limit:
        tasks = tasks[:limit]

    return tasks

def handle_prioritize(args):
    """
    Calls AI to prioritize tasks. Gathers tasks from OmniFocus,
    sends them to OpenAI or Anthropic, and prints the AI's recommendations.
    """
    project_name = args.project
    limit = args.limit
    focus_on_finance = args.finance
    deduplicate = args.deduplicate
    
    # Fetch tasks using the new helper function
    tasks = get_tasks_for_prioritization(project_name, limit, focus_on_finance)
    
    if not tasks:
        print("No tasks found to prioritize.")
        return
    
    # Special handling for deduplication mode
    if deduplicate:
        handle_deduplication(tasks)
        return
    
    # Special handling for finance focus
    if focus_on_finance:
        handle_finance_project(tasks)
        return
    
    # Send to AI for prioritization
    print(f"Analyzing {len(tasks)} tasks with AI...")
    prioritized_tasks = ai_utils.prioritize_tasks(tasks)
    
    # Display results
    print(format_priority_recommendations(prioritized_tasks))

def handle_deduplication(tasks):
    """Handle task deduplication specifically"""
    # Find potential duplicates
    potential_duplicates = ai_utils.find_duplicate_tasks(tasks)
    
    if not potential_duplicates:
        print("No potential duplicate tasks found.")
        return
    
    # Format duplicates for display
    print(f"Found {len(potential_duplicates)} potential duplicate task pairs:")
    print("\nPotential Duplicates:")
    for i, (task1, task2) in enumerate(potential_duplicates):
        print(f"{i+1}. '{task1.name}' and '{task2.name}'")
    
    # Analyze with AI
    print("\nAnalyzing duplicates with AI...")
    
    # Create a detailed input for AI
    duplicate_details = []
    for i, (task1, task2) in enumerate(potential_duplicates):
        task1_due = f", Due: {task1.due_date}" if task1.due_date else ""
        task2_due = f", Due: {task2.due_date}" if task2.due_date else ""
        
        task1_note = f", Note: {task1.note[:100]}..." if task1.note and len(task1.note) > 0 else ""
        task2_note = f", Note: {task2.note[:100]}..." if task2.note and len(task2.note) > 0 else ""
        
        duplicate_details.append(f"## Duplicate Pair {i+1}:")
        duplicate_details.append(f"1. ID: {task1.id}, Name: '{task1.name}'{task1_due}{task1_note}")
        duplicate_details.append(f"2. ID: {task2.id}, Name: '{task2.name}'{task2_due}{task2_note}")
        duplicate_details.append("")
    
    # Get template for deduplication
    template = get_prompt_template("task_deduplication", 
                                  "# Task Deduplication Request\n\nI need help identifying and consolidating duplicate tasks in my OmniFocus system...")
    
    # Replace placeholder with actual duplicate info
    prompt = template.replace("{potential_duplicates}", "\n".join(duplicate_details))
    
    # Choose AI service
    use_anthropic = os.environ.get("USE_ANTHROPIC", "").lower() in ('true', '1', 'yes')
    
    try:
        if use_anthropic:
            from ai_integration.anthropic_client import anthropic_completion
            response = anthropic_completion(prompt)
        else:
            from ai_integration.openai_client import openai_completion
            response = openai_completion(prompt)
        
        print("\n" + response)
    except Exception as e:
        print(f"Error calling AI service: {str(e)}. Please check your API keys.")
        # Fallback to simple recommendations
        print("\nFallback Recommendations:")
        for i, (task1, task2) in enumerate(potential_duplicates):
            print(f"Pair {i+1}: '{task1.name}' and '{task2.name}' appear to be duplicates.")
            print(f"  - Consider keeping '{task1.name}' if it has more details.")
            print(f"  - Or clarify the purpose of each if they are distinct tasks.\n")

def handle_finance_project(tasks):
    """Handle organization and simplification of finance project"""
    # Format tasks for the AI
    finance_task_details = []
    for i, task in enumerate(tasks):
        due_date_str = f", Due: {task.due_date}" if task.due_date else ""
        project_str = f", Project: {task.project}" if hasattr(task, 'project') and task.project else ""
        note_preview = f", Note: {task.note[:50]}..." if task.note and len(task.note) > 0 else ""
        
        finance_task_details.append(f"{i+1}. {task.name}{due_date_str}{project_str}{note_preview}")
    
    # Get finance project organization template
    template = get_prompt_template("finance_project_organization", 
                                  "# Finance Project Organization Request\n\nI need help organizing and simplifying my finance-related tasks...")
    
    # Replace placeholder with actual finance task info
    prompt = template.replace("{finance_tasks}", "\n".join(finance_task_details))
    
    print(f"Analyzing {len(tasks)} finance-related tasks with AI...")
    
    # Choose AI service
    use_anthropic = os.environ.get("USE_ANTHROPIC", "").lower() in ('true', '1', 'yes')
    
    try:
        if use_anthropic:
            from ai_integration.anthropic_client import anthropic_completion
            response = anthropic_completion(prompt)
        else:
            from ai_integration.openai_client import openai_completion
            response = openai_completion(prompt)
        
        # Format as markdown
        lines = ["# Finance Project Organization Recommendations", ""]
        lines.extend(response.split('\n'))
        
        print("\n" + "\n".join(lines))
    except Exception as e:
        print(f"Error calling AI service: {str(e)}. Please check your API keys.")
        # Fallback to basic organization
        print("\nFallback Finance Organization Recommendations:")
        
        # Group by categories using simple keyword matching
        categories = {
            "Budgeting": [],
            "Investments": [],
            "Taxes": [],
            "Banking": [],
            "Planning": [],
            "Other": []
        }
        
        for task in tasks:
            task_text = f"{task.name} {task.note}".lower()
            
            if any(kw in task_text for kw in ["budget", "expense", "spend"]):
                categories["Budgeting"].append(task)
            elif any(kw in task_text for kw in ["invest", "stock", "fund", "portfolio"]):
                categories["Investments"].append(task)
            elif any(kw in task_text for kw in ["tax", "irs", "return"]):
                categories["Taxes"].append(task)
            elif any(kw in task_text for kw in ["bank", "account", "transfer", "deposit"]):
                categories["Banking"].append(task)
            elif any(kw in task_text for kw in ["plan", "goal", "future", "retire"]):
                categories["Planning"].append(task)
            else:
                categories["Other"].append(task)
        
        # Print organized tasks
        for category, category_tasks in categories.items():
            if category_tasks:
                print(f"\n## {category} Tasks:")
                for i, task in enumerate(category_tasks):
                    print(f"{i+1}. {task.name}")

