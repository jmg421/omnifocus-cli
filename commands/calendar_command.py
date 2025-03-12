import datetime
from typing import List
from omnifocus_api import apple_script_client
from ai_integration.ical_integration import fetch_calendar_events, sync_with_calendar

def handle_calendar(args):
    """
    Sync OmniFocus tasks with iCal calendars to verify reality status.
    """
    # Get calendar URL from args or config
    calendar_url = args.calendar_url
    project = args.project
    
    # Set date range (default to next 30 days)
    start_date = datetime.datetime.now()
    end_date = start_date + datetime.timedelta(days=30)
    
    print(f"Fetching calendar events from {calendar_url}...")
    try:
        calendar_events = fetch_calendar_events(calendar_url, start_date, end_date)
    except Exception as e:
        print(f"Error fetching calendar events: {str(e)}")
        return
    
    print(f"Found {len(calendar_events)} calendar events")
    
    # Fetch tasks from OmniFocus
    print("Fetching tasks from OmniFocus...")
    tasks = apple_script_client.fetch_tasks(project_name=project)
    
    if not tasks:
        print("No tasks found in OmniFocus.")
        return
    
    # Sync tasks with calendar events
    print("Analyzing task reality status...")
    reality_status = sync_with_calendar(tasks, calendar_events)
    
    # Print results
    print("\nTask Reality Status:")
    print("=" * 50)
    
    real_tasks = []
    unreal_tasks = []
    
    for task in tasks:
        is_real = reality_status.get(task.id, False)
        if is_real:
            real_tasks.append(task)
        else:
            unreal_tasks.append(task)
    
    if real_tasks:
        print("\nVerified Real Tasks:")
        print("-" * 20)
        for task in real_tasks:
            print(f"✓ {task.name}")
    
    if unreal_tasks:
        print("\nUnverified Tasks (Not Found in Calendar):")
        print("-" * 35)
        for task in unreal_tasks:
            print(f"? {task.name}")
    
    # Print summary
    total = len(tasks)
    real_count = len(real_tasks)
    print(f"\nSummary: {real_count}/{total} tasks verified as real ({(real_count/total)*100:.1f}%)") 