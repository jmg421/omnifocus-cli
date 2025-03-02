from omnifocus_api import apple_script_client
from ai_integration import ai_utils
from ai_integration.utils.format_utils import format_priority_recommendations

def handle_prioritize(args):
    """
    Calls AI to prioritize tasks. Gathers tasks from OmniFocus,
    sends them to OpenAI or Anthropic, and prints the AI's recommendations.
    """
    project_name = args.project
    limit = args.limit
    
    # Get tasks from OmniFocus
    print(f"Getting tasks from OmniFocus{' for project: ' + project_name if project_name else ''}...")
    tasks = apple_script_client.fetch_tasks(project_name=project_name)
    
    # Limit the number of tasks if needed
    if limit and len(tasks) > limit:
        tasks = tasks[:limit]
    
    if not tasks:
        print("No tasks found to prioritize.")
        return
    
    # Send to AI for prioritization
    print(f"Analyzing {len(tasks)} tasks with AI...")
    prioritized_tasks = ai_utils.prioritize_tasks(tasks)
    
    # Display results
    print(format_priority_recommendations(prioritized_tasks))

