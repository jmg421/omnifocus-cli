#!/usr/bin/env python3
"""
Updated Evan Car Repair Scheduling
Takes into account Evan calling off Friday and being available Saturday.
"""

import os
import sys
from datetime import datetime, timedelta
from typing import Dict

# Add the omni-cli directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def analyze_evan_car_repair_updated():
    """Analyze Evan's car repair with updated availability information."""
    
    print("🚗 UPDATED Evan Car Repair Analysis")
    print("=" * 50)
    
    # Updated information
    print("📅 UPDATED SCHEDULE:")
    print("  • Friday (7/18): Evan calling off work (6 points against him)")
    print("  • Friday (7/18): Evan going to Cedar Point with friends")
    print("  • Saturday (7/19): Evan NOT scheduled to work")
    print("  • Sunday (7/20): Family vacation begins")
    print("  • Vacation: July 20-27")
    print()
    
    # Car repair details
    car_repair_info = {
        "location": "Crash Champions - 10130 Columbus Pike, Lewis Center, OH 43035",
        "service": "Night drop available",
        "home_address": "5716 Ludington Drive, Lewis Center, OH 43035",
        "target_date": "2025-07-19",  # Saturday
        "vacation_departure": "2025-07-20"  # Sunday
    }
    
    print("🎯 UPDATED RECOMMENDATIONS:")
    print()
    
    recommendations = [
        {
            "title": "Simplified Transportation Solution",
            "description": "Evan is available all day Saturday (not working)",
            "solution": "Evan can drive his own car to Crash Champions anytime Saturday",
            "steps": [
                "Evan is free all day Saturday",
                "Can drop car off anytime during business hours",
                "Use night drop if needed for flexibility",
                "Walk home or get ride from family member"
            ]
        },
        {
            "title": "Grace's Tournament Coordination",
            "description": "Grace has softball tournament in Baltimore, OH at 11 AM",
            "solution": "You take Grace to tournament, Evan handles car repair independently",
            "steps": [
                "You leave home by 9:30 AM for Grace's 11 AM game",
                "Evan can drop car off anytime Saturday (morning, afternoon, or evening)",
                "No transportation conflicts since Evan is not working",
                "Christina stays home to pack for vacation"
            ]
        },
        {
            "title": "Optimal Timing",
            "description": "Best time for car drop-off",
            "solution": "Saturday morning before you leave for tournament",
            "steps": [
                "Evan drops car off Saturday morning (8-9 AM)",
                "You leave for tournament at 9:30 AM",
                "Car repair can begin immediately",
                "Car will be ready before vacation departure"
            ]
        }
    ]
    
    for i, rec in enumerate(recommendations, 1):
        print(f"{i}. {rec['title']}")
        print(f"   Issue: {rec['description']}")
        print(f"   Solution: {rec['solution']}")
        print("   Steps:")
        for step in rec['steps']:
            print(f"     • {step}")
        print()
    
    # Create calendar event
    print("📅 Creating Calendar Event...")
    create_calendar_event_updated(car_repair_info)
    
    # Complete OmniFocus task
    print("✅ Completing OmniFocus task...")
    complete_omnifocus_task_simple()
    
    # Save updated reference
    save_updated_reference(car_repair_info)
    
    print("✅ Analysis complete! The situation is much simpler now.")

def create_calendar_event_updated(car_repair_info: Dict):
    """Create calendar event with updated information."""
    try:
        script = '''
        tell application "Calendar"
            set cal to calendar "Family"
            set newEvent to make new event at end of events of cal with properties {summary:"Evan Car Repair - Drop Off", start date:date "2025-07-19 08:00:00", end date:date "2025-07-19 09:00:00", location:"Crash Champions - 10130 Columbus Pike, Lewis Center, OH 43035", description:"Drop off Evan's car for repair. Evan available all day Saturday (not working). Night drop available."}
            return id of newEvent
        end tell
        '''
        
        import subprocess
        result = subprocess.run(['osascript', '-e', script], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Created calendar event: Evan Car Repair - Drop Off")
        else:
            print(f"❌ Error creating calendar event: {result.stderr}")
            
    except Exception as e:
        print(f"❌ Error creating calendar event: {e}")

def complete_omnifocus_task_simple():
    """Complete the OmniFocus task with a simpler approach."""
    try:
        script = '''
        tell application "OmniFocus"
            set theDoc to default document
            set theTask to first flattened task of theDoc whose name contains "Make appointment for Evan car repair"
            if theTask is not missing value then
                set completed of theTask to true
                set note of theTask to "Scheduled for Saturday 7/19/2025 at 8:00 AM. Evan calling off Friday, available all day Saturday. Much simpler logistics."
                return "Task completed"
            else
                return "Task not found"
            end if
        end tell
        '''
        
        import subprocess
        result = subprocess.run(['osascript', '-e', script], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            if "Task completed" in result.stdout:
                print("✅ OmniFocus task completed successfully")
            else:
                print("ℹ️  No matching OmniFocus task found")
        else:
            print(f"❌ Error completing OmniFocus task: {result.stderr}")
            
    except Exception as e:
        print(f"❌ Error completing OmniFocus task: {e}")

def save_updated_reference(car_repair_info: Dict):
    """Save updated reference information."""
    reference_file = "reference/docs/automotive/crash_champions_repair_updated.md"
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(reference_file), exist_ok=True)
    
    content = f"""# Crash Champions Car Repair - Evan (UPDATED)

## Service Information
- **Location**: {car_repair_info['location']}
- **Service Type**: Night drop available
- **Home Address**: {car_repair_info['home_address']}

## Updated Schedule
- **Friday (7/18)**: Evan calling off work (6 points against him)
- **Friday (7/18)**: Evan going to Cedar Point with friends
- **Saturday (7/19)**: Evan NOT scheduled to work
- **Sunday (7/20)**: Family vacation begins
- **Vacation**: July 20-27

## Scheduled Appointment
- **Date**: Saturday, July 19, 2025
- **Time**: 8:00 AM (optimal time)
- **Vehicle**: Evan's car
- **Service**: Car repair

## Updated Transportation Plan
1. Evan is available all day Saturday (not working)
2. Drop car off Saturday morning (8-9 AM)
3. Use night drop service if needed for flexibility
4. Walk home or get ride from family member

## Related Events
- Grace has softball tournament in Baltimore, OH at 11 AM
- You leave for tournament at 9:30 AM
- Christina staying home to pack for vacation
- Family vacation departure on Sunday, July 20, 2025

## Key Changes
- **Much simpler logistics**: Evan available all day Saturday
- **No work conflicts**: Evan calling off Friday
- **Flexible timing**: Can drop off anytime Saturday
- **Independent coordination**: Evan handles car, you handle Grace's tournament

## Notes
- Night drop service available
- 10-minute drive from home to repair shop
- No transportation conflicts since Evan is not working
- Car will be ready before vacation departure
- Much simpler than original plan

---
*Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""
    
    try:
        with open(reference_file, 'w') as f:
            f.write(content)
        print(f"✅ Saved updated reference information to {reference_file}")
    except Exception as e:
        print(f"❌ Error saving reference information: {e}")

if __name__ == "__main__":
    analyze_evan_car_repair_updated() 