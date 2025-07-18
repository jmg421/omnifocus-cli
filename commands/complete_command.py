from omnifocus_api.apple_script_client import execute_omnifocus_applescript

def generate_complete_task_applescript(task_id: str) -> str:
    """Generate AppleScript that marks the given task as completed."""
    # Use OmniFocus's `mark complete` verb which safely handles dates & subtasks.
    script = f"""
    tell application \"OmniFocus\"
        tell default document
            try
                set theTask to first flattened task whose id is \"{task_id}\"
                -- Only mark if not already completed
                if completed of theTask is false then
                    mark complete theTask
                end if
                return \"Task {task_id} marked complete.\"
            on error errMsg number errNum
                if errNum is -1728 then
                    return \"Error: Task with ID {task_id} not found. (errNum: \" & errNum & \")\"
                else
                    return \"Error completing task {task_id}: \" & errMsg & \" (Num: \" & errNum & \")\"
                end if
            end try
        end tell
    end tell
    """
    return script


def handle_complete(args):
    """Mark one or more tasks complete in OmniFocus using AppleScript."""
    task_ids = args.task_id if isinstance(args.task_id, (list, tuple)) else [args.task_id]

    if not task_ids:
        print("Error: At least one task ID must be supplied to complete.")
        return

    for tid in task_ids:
        print(f"→ Completing task ID: {tid}")
        applescript = generate_complete_task_applescript(tid)
        try:
            result = execute_omnifocus_applescript(applescript)
            print(result)
            if not str(result).startswith("Error"):
                print("   ✔ Success\n")
            else:
                print("   ⚠︎ Failure reported\n")
        except Exception as e:
            print(f"   ⚠︎ Exception while marking {tid} complete: {e}\n")

