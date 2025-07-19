from ..omnifocus_api import apple_script_client
from ..ai_integration.imessage_integration import sync_messages_to_tasks
import sys

def handle_imessage(args):
    """
    Sync iMessage conversations with OmniFocus tasks.
    """
    contact = args.contact
    project = args.project
    
    print(f"Syncing messages from {contact}...")
    try:
        action_items = sync_messages_to_tasks(contact, project)
        
        if not action_items:
            print("\nNo action items found in recent messages.")
            print("\nThis could be because:")
            print("1. No messages found for this contact")
            print("2. No messages contain potential action items")
            print("3. Messages are older than 30 days")
            print("\nTips:")
            print("- Try using the contact's full name or phone number")
            print("- Check if you have any recent messages with this contact")
            print("- Make sure Terminal.app has Full Disk Access in System Settings")
            return
        
        print(f"\nFound {len(action_items)} potential action items:")
        print("=" * 50)
        
        # Create tasks for each action item
        created_count = 0
        for item in action_items:
            print(f"\nPotential task from message on {item['date']}:")
            print(f"Title: {item['title']}")
            
            # Create the task in OmniFocus
            success, task_id = apple_script_client.create_task_via_applescript(
                title=item['title'],
                project_name=project,
                note=item['note'],
                due_date=item['due_date']
            )
            
            if success:
                created_count += 1
                print("✓ Created task in OmniFocus")
            else:
                print("✗ Failed to create task")
        
        # Print summary
        print("\nSummary:")
        print(f"- Found {len(action_items)} potential action items")
        print(f"- Successfully created {created_count} tasks in OmniFocus")
        if project:
            print(f"- Tasks added to project: {project}")
        else:
            print("- Tasks added to inbox")
            
    except PermissionError as e:
        print(f"\nError: {str(e)}")
        print("\nTo fix this:")
        print("1. Open System Settings")
        print("2. Go to Privacy & Security > Full Disk Access")
        print("3. Click the '+' button")
        print("4. Navigate to /Applications/Utilities/")
        print("5. Select 'Terminal.app' (or your terminal app)")
        print("6. Restart your terminal and try again")
        
    except Exception as e:
        print(f"\nUnexpected error: {str(e)}")
        print("Please check your contact information and try again.") 