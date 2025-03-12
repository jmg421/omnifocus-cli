from typing import Optional
from omnifocus_api import apple_script_client
from ai_integration.imessage_integration import scan_recent_action_items

def get_user_input(prompt: str, valid_options: list) -> str:
    """Get user input with validation."""
    while True:
        response = input(prompt).strip().lower()
        if response in valid_options:
            return response
        print(f"Please enter one of: {', '.join(valid_options)}")

def handle_scan(args):
    """
    Scan recent messages for action items and interactively add them to OmniFocus.
    """
    days = args.days
    project = args.project
    
    print(f"Scanning messages from the last {days} days...")
    try:
        action_items = scan_recent_action_items(days)
        
        if not action_items:
            print("\nNo action items found in recent messages.")
            print("\nThis could be because:")
            print("1. No messages contain potential action items")
            print("2. Messages are too old")
            print("\nTips:")
            print("- Try increasing the number of days to scan")
            print("- Make sure Terminal.app has Full Disk Access in System Settings")
            return
        
        print(f"\nFound {len(action_items)} potential action items:")
        print("=" * 50)
        
        # Group items by contact
        items_by_contact = {}
        for item in action_items:
            contact = item['contact']
            if contact not in items_by_contact:
                items_by_contact[contact] = []
            items_by_contact[contact].append(item)
        
        # Process items by contact
        created_count = 0
        for contact, items in items_by_contact.items():
            print(f"\nMessages from {contact}:")
            print("-" * 30)
            
            for item in items:
                print(f"\nDate: {item['date']}")
                print(f"Message: {item['title']}")
                
                # Ask user what to do
                response = get_user_input(
                    "\nAdd this as a task? (y)es/(n)o/(q)uit: ",
                    ['y', 'n', 'q']
                )
                
                if response == 'q':
                    break
                elif response == 'y':
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
            
            if response == 'q':
                break
        
        # Print summary
        print("\nSummary:")
        print(f"- Scanned {len(action_items)} potential action items")
        print(f"- Added {created_count} tasks to OmniFocus")
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
        print("Please try again with different parameters.") 