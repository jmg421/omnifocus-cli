#!/usr/bin/env python3
"""
Schedule Car Repair Command
Handles complex scheduling scenarios like Evan's car repair with calendar integration.
"""

import os
import sys
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional

# Add the omni-cli directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from ai_integration.calendar_analyzer import CalendarAnalyzer, analyze_scheduling_scenario

def schedule_evan_car_repair():
    """Handle Evan's car repair scheduling with calendar analysis."""
    
    print("🚗 Evan's Car Repair Scheduling Analysis")
    print("=" * 50)
    
    # Known information
    car_repair_info = {
        "location": "Crash Champions - 10130 Columbus Pike, Lewis Center, OH 43035",
        "service": "Night drop available",
        "home_address": "5716 Ludington Drive, Lewis Center, OH 43035",
        "target_date": "2025-07-19",  # Saturday
        "vacation_departure": "2025-07-20"  # Sunday
    }
    
    print(f"📍 Repair Location: {car_repair_info['location']}")
    print(f"🏠 Home Address: {car_repair_info['home_address']}")
    print(f"📅 Target Date: {car_repair_info['target_date']} (Saturday)")
    print(f"✈️  Vacation Departure: {car_repair_info['vacation_departure']} (Sunday)")
    print()
    
    # Analyze the scheduling scenario
    print("🔍 Analyzing Calendar Conflicts...")
    scenario = analyze_scheduling_scenario(
        car_repair_info['target_date'],
        "Evan car repair at Crash Champions while Grace has softball tournament in Baltimore"
    )
    
    print(f"📊 Found {scenario['events_found']} events, {scenario['conflicts']} conflicts")
    print()
    
    # Display conflicts
    if scenario['conflict_details']:
        print("⚠️  SCHEDULING CONFLICTS:")
        for i, conflict in enumerate(scenario['conflict_details'], 1):
            print(f"  {i}. {conflict['description']} ({conflict['severity']})")
        print()
    
    # Display solutions
    if scenario['solution_details']:
        print("💡 RECOMMENDED SOLUTIONS:")
        for i, solution in enumerate(scenario['solution_details'], 1):
            print(f"  {i}. {solution['description']} (Impact: {solution['impact']})")
            for step in solution['steps']:
                print(f"     - {step}")
        print()
    
    # Specific recommendations for this scenario
    print("🎯 SPECIFIC RECOMMENDATIONS FOR EVAN'S CAR REPAIR:")
    print()
    
    recommendations = [
        {
            "title": "Transportation Solution",
            "description": "Evan can't drive his car while working at Kroger (8 AM - 4 PM)",
            "solution": "Use night drop at Crash Champions after Evan gets off work",
            "steps": [
                "Evan finishes work at 4 PM",
                "Drive car to Crash Champions (10 min from home)",
                "Use night drop service",
                "Walk home or get ride from family member"
            ]
        },
        {
            "title": "Grace's Tournament Transportation",
            "description": "Grace has softball tournament in Baltimore, OH (1.5 hours away) at 11 AM",
            "solution": "You take Grace to tournament while Christina stays home to pack",
            "steps": [
                "Leave home by 9:30 AM for 11 AM game",
                "Account for warmup time",
                "Christina stays home to pack for vacation",
                "Coordinate return time based on tournament schedule"
            ]
        },
        {
            "title": "Timeline Coordination",
            "description": "Need to coordinate car drop-off with tournament schedule",
            "solution": "Drop car off Saturday evening after tournament",
            "steps": [
                "Return from tournament (estimated 2-3 PM)",
                "Evan gets off work at 4 PM",
                "Drop car at Crash Champions around 4:30 PM",
                "Use night drop service"
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
    
    # Ask user if they want to create calendar events
    print("📅 Would you like to create calendar events for this plan?")
    response = input("Create events? (y/n): ").lower().strip()
    
    if response == 'y':
        create_calendar_events(car_repair_info)
    
    # Complete the OmniFocus task
    print("✅ Completing OmniFocus task...")
    complete_omnifocus_task()
    
    # Save reference information
    save_reference_info(car_repair_info)

def create_calendar_events(car_repair_info: Dict):
    """Create calendar events for the car repair plan."""
    analyzer = CalendarAnalyzer()
    
    # Create events
    events_to_create = [
        {
            "title": "Evan Car Repair - Drop Off",
            "start_time": datetime(2025, 7, 19, 16, 30),  # 4:30 PM
            "end_time": datetime(2025, 7, 19, 17, 0),     # 5:00 PM
            "location": car_repair_info['location'],
            "calendar": "Family",
            "description": f"Drop off Evan's car for repair using night drop service. Home: {car_repair_info['home_address']}"
        },
        {
            "title": "Grace Softball Tournament - Baltimore",
            "start_time": datetime(2025, 7, 19, 9, 30),   # 9:30 AM departure
            "end_time": datetime(2025, 7, 19, 15, 0),     # 3:00 PM return (estimated)
            "location": "1101 N Romulus St, Baltimore, OH",
            "calendar": "Grace",
            "description": "Softball tournament. Depart 9:30 AM for 11 AM game. Account for warmup time."
        }
    ]
    
    for event in events_to_create:
        success = analyzer.create_calendar_event(
            title=event['title'],
            start_time=event['start_time'],
            end_time=event['end_time'],
            location=event['location'],
            calendar_name=event['calendar']
        )
        
        if success:
            print(f"✅ Created: {event['title']}")
        else:
            print(f"❌ Failed to create: {event['title']}")

def complete_omnifocus_task():
    """Complete the OmniFocus task for Evan's car repair."""
    try:
        # Use AppleScript to complete the task
        script = '''
        tell application "OmniFocus"
            set theDoc to default document
            set theTask to first flattened task of theDoc whose name contains "Make appointment for Evan car repair"
            set completed of theTask to true
            set note of theTask to "Scheduled for Saturday 7/19/2025 at 4:30 PM using night drop at Crash Champions. Grace has tournament in Baltimore - coordinated transportation."
        end tell
        '''
        
        import subprocess
        result = subprocess.run(['osascript', '-e', script], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ OmniFocus task completed successfully")
        else:
            print(f"❌ Error completing OmniFocus task: {result.stderr}")
            
    except Exception as e:
        print(f"❌ Error completing OmniFocus task: {e}")

def save_reference_info(car_repair_info: Dict):
    """Save car repair information to reference system."""
    reference_file = "reference/docs/automotive/crash_champions_repair.md"
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(reference_file), exist_ok=True)
    
    content = f"""# Crash Champions Car Repair - Evan

## Service Information
- **Location**: {car_repair_info['location']}
- **Service Type**: Night drop available
- **Home Address**: {car_repair_info['home_address']}

## Scheduled Appointment
- **Date**: Saturday, July 19, 2025
- **Time**: 4:30 PM (night drop)
- **Vehicle**: Evan's car
- **Service**: Car repair

## Transportation Plan
1. Evan finishes work at Kroger at 4 PM
2. Drive car to Crash Champions (10 min from home)
3. Use night drop service
4. Walk home or get ride from family member

## Related Events
- Grace has softball tournament in Baltimore, OH at 11 AM
- Family vacation departure on Sunday, July 20, 2025
- Christina staying home to pack while John takes Grace to tournament

## Notes
- Night drop service available
- 10-minute drive from home to repair shop
- Coordinated with Grace's tournament schedule
- Car will be ready before vacation departure

---
*Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""
    
    try:
        with open(reference_file, 'w') as f:
            f.write(content)
        print(f"✅ Saved reference information to {reference_file}")
    except Exception as e:
        print(f"❌ Error saving reference information: {e}")

if __name__ == "__main__":
    schedule_evan_car_repair() 