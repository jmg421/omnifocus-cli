from ..omnifocus_api import apple_script_client

def handle_complete(args):
    """
    Mark one or more tasks complete.
    """
    for tid in args.task_id:
        success = apple_script_client.complete_task(tid)
        if success:
            print(f"Task {tid} marked complete.")
        else:
            print(f"Failed to mark task {tid} complete.")

