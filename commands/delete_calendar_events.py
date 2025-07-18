#!/usr/bin/env python3
"""
Delete Calendar Events
Delete calendar events by title to clean up old events with incorrect times.
"""

import os
import sys
import subprocess

def delete_calendar_events_by_title(title: str, calendar_name: str = "Family"):
    """Delete calendar events by title."""
    try:
        script = f'''tell application "Calendar"
set cal to calendar "{calendar_name}"
set eventsToDelete to {{}}
repeat with evt in events of cal
    if summary of evt contains "{title}" then
        set end of eventsToDelete to evt
    end if
end repeat
repeat with evt in eventsToDelete
    delete evt
end repeat
return count of eventsToDelete
end tell'''
        
        result = subprocess.run(['osascript', '-e', script], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            count = result.stdout.strip()
            print(f"✅ Deleted {count} events with title containing '{title}' from {calendar_name} calendar")
            return True
        else:
            print(f"❌ Error deleting events: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Error deleting events: {e}")
        return False

def delete_evan_car_repair_events():
    """Delete all Evan car repair related events to clean up."""
    print("🧹 Cleaning up old Evan car repair events...")
    
    # Delete from Family calendar
    delete_calendar_events_by_title("Drop off Evan's car at Crash Champions", "Family")
    delete_calendar_events_by_title("Evan Car Repair", "Family")
    
    # Delete from Evan calendar
    delete_calendar_events_by_title("Drop off Evan's car at Crash Champions", "Evan")
    delete_calendar_events_by_title("Evan Car Repair", "Evan")
    
    # Delete from John calendar
    delete_calendar_events_by_title("Drop off Evan's car at Crash Champions", "John")
    delete_calendar_events_by_title("Evan Car Repair", "John")
    
    print("✅ Cleanup complete!")

if __name__ == "__main__":
    delete_evan_car_repair_events() 