from omnifocus_api import apple_script_client
from ai_integration.ai_utils import create_delegation_email_body
from ai_integration.utils.config import get_config
from ai_integration.utils.prompt_utils import confirm_action
import smtplib

def handle_delegation(args):
    """
    Delegates the specified task to someone else. Could:
      1) Mark the task as delegated in OmniFocus (e.g., add a 'Waiting' tag).
      2) Send an email or message to that person with details.
    """
    task_id = args.task_id
    delegate_to = args.to
    method = args.method

    # 1. Fetch task details
    task = apple_script_client.get_task_by_id(task_id)
    if not task:
        print(f"Task {task_id} not found.")
        return

    print(f"Preparing to delegate task '{task.name}' to {delegate_to} via {method}.")
    if not confirm_action("Proceed with delegation?"):
        print("Delegation canceled.")
        return

    # 2. Mark the task as delegated in OmniFocus
    updated = apple_script_client.add_tag_to_task(task_id, tag_name="Waiting")
    if not updated:
        print("Could not update the task with 'Waiting' tag.")
        return

    # 3. Construct email body using AI (optional)
    email_body = create_delegation_email_body(task.name, task.note, delegate_to)

    # 4. Actually send the delegation message (example only, might integrate with Apple Mail, etc.)
    print(f"--- Email Preview ---\nTo: {delegate_to}\nSubject: Delegation: {task.name}\n\n{email_body}")
    print("Email not automatically sent in this example. Implement your mail integration here.")

