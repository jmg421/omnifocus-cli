from typing import List
from omnifocus_api.data_models import OmniFocusTask
# from ai_integration.openai_client import openai_completion
# from ai_integration.anthropic_client import anthropic_completion

def prioritize_tasks(tasks: List[OmniFocusTask]) -> List[str]:
    """
    MOCK IMPLEMENTATION: Prioritizes tasks without calling an external API.
    Returns a list of recommendations (strings).
    """
    if not tasks:
        return ["No tasks to prioritize."]
    
    # Create a simple task list
    task_descriptions = [f"{i+1}. {task.name}" for i, task in enumerate(tasks)]
    
    # Create mock recommendations based on task names
    recommendations = []
    
    # Sort tasks by any time information in square brackets
    time_tasks = []
    other_tasks = []
    
    for task in tasks:
        if '[' in task.name and ']' in task.name:
            # Extract time if available
            try:
                time_str = task.name.split('[')[1].split(']')[0]
                time_tasks.append((time_str, task))
            except:
                other_tasks.append(task)
        else:
            other_tasks.append(task)
    
    # Sort time_tasks by the time
    time_tasks.sort(key=lambda x: x[0])
    
    # Create recommendations
    recommendations.append("# Task Prioritization Recommendations")
    recommendations.append("")
    recommendations.append("Here's how I would prioritize your tasks:")
    recommendations.append("")
    
    # First recommend time-sensitive tasks in chronological order
    if time_tasks:
        recommendations.append("## Time-Sensitive Tasks (in chronological order)")
        for i, (time, task) in enumerate(time_tasks):
            recommendations.append(f"{i+1}. **{task.name}** - This task has a specific time and should be done according to schedule.")
        recommendations.append("")
    
    # Then recommend other tasks
    if other_tasks:
        recommendations.append("## Other Tasks")
        for i, task in enumerate(other_tasks):
            recommendations.append(f"{i+1}. **{task.name}** - No specific time requirement, can be done when time permits.")
    
    return recommendations

def create_delegation_email_body(task_name: str, task_note: str, delegate_to: str) -> str:
    """
    Creates a mock email body for delegating a task.
    """
    return f"""Subject: Task Delegation: {task_name}

Hi {delegate_to},

I hope this email finds you well. I'd like to delegate the following task to you:

Task: {task_name}
Details: {task_note}

Could you please let me know if you can take this on and provide an estimated timeline for completion?

Thanks in advance for your help!

Best regards,
[Your Name]"""

