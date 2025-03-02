import json
from omnifocus_api import apple_script_client
from ai_integration.utils.format_utils import format_task_list

def handle_list(args):
    """
    Lists tasks in OmniFocus, optionally filtered by project.
    """
    project_name = args.project
    tasks = apple_script_client.fetch_tasks(project_name)

    if args.json:
        print(json.dumps([task.to_dict() for task in tasks], indent=2))
    else:
        output = format_task_list(tasks)
        print(output)

