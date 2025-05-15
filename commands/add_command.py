from ..omnifocus_api import apple_script_client
from ..ai_integration.utils.format_utils import parse_date_string

def handle_add(args):
    """
    Creates a new task in OmniFocus with the provided arguments.
    """
    title = args.title
    project = args.project
    note = args.note or ""
    due_date = parse_date_string(args.due) if args.due else None

    success, of_task_id = apple_script_client.create_task_via_applescript(
        title=title,
        project_name=project,
        note=note,
        due_date=due_date
    )

    if success:
        print(f"Task '{title}' created in OmniFocus (ID: {of_task_id}).")
    else:
        print(f"Failed to create task '{title}' in OmniFocus.")

