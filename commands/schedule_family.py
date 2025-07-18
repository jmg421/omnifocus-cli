#!/usr/bin/env python3
"""
Generic Family Scheduling Command
Handles any family scheduling scenario with calendar integration and conflict analysis.
"""

import os
import sys
import json
import argparse
from datetime import datetime, timedelta
from typing import Dict, List, Optional

# Add the omni-cli directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from ai_integration.family_scheduler import (
    FamilyScheduler, ScheduleRequest, FamilyMember, Location,
    create_scheduling_request, analyze_family_scheduling
)

def schedule_family_event(title: str, description: str, date_str: str,
                         location_name: str, attendees: List[str],
                         duration_minutes: int = 60, priority: str = "medium",
                         create_calendar_event: bool = False, time_str: str = "08:00",
                         task_id: Optional[str] = None) -> Dict:
    """Schedule a family event with comprehensive analysis."""
    
    print(f"📅 Family Scheduling Analysis: {title}")
    print("=" * 60)
    
    # Create scheduling request with time_str
    request = create_scheduling_request(
        title=title,
        description=description,
        date_str=date_str,
        location_name=location_name,
        attendees=attendees,
        duration_minutes=duration_minutes,
        time_str=time_str
    )
    
    # Set priority
    request.priority = priority
    
    # Create scheduler and analyze
    scheduler = FamilyScheduler()
    analysis = scheduler.analyze_scheduling_request(request)
    
    # Display analysis results
    print(f"📊 Analysis Results:")
    print(f"   • Calendar Events Found: {analysis['calendar_events']}")
    print(f"   • Conflicts Identified: {analysis['conflicts']}")
    print(f"   • Solutions Generated: {analysis['solutions']}")
    print()
    
    # Display conflicts
    if analysis['conflict_details']:
        print("⚠️  SCHEDULING CONFLICTS:")
        for i, conflict in enumerate(analysis['conflict_details'], 1):
            print(f"  {i}. {conflict['description']} ({conflict['severity']})")
            print(f"     Affected: {', '.join(conflict['affected_members'])}")
        print()
    
    # Display solutions
    if analysis['solution_details']:
        print("💡 RECOMMENDED SOLUTIONS:")
        for i, solution in enumerate(analysis['solution_details'], 1):
            print(f"  {i}. {solution['description']} (Impact: {solution['impact']})")
            print(f"     Coordination needed: {', '.join(solution['coordination_needed'])}")
            print("     Steps:")
            for step in solution['steps']:
                print(f"       • {step}")
        print()
    
    # Ask user for action
    if analysis['conflicts'] > 0:
        print("🤔 How would you like to proceed?")
        print("  1. Create calendar event anyway")
        print("  2. Reschedule to avoid conflicts")
        print("  3. Delegate to another family member")
        print("  4. Cancel scheduling")
        
        choice = input("Enter choice (1-4): ").strip()
        
        if choice == "1":
            create_calendar_event = True
        elif choice == "2":
            # Suggest alternative times
            suggest_alternative_times(scheduler, request)
            return analysis
        elif choice == "3":
            # Suggest delegation
            suggest_delegation(scheduler, request)
            return analysis
        elif choice == "4":
            print("❌ Scheduling cancelled.")
            return analysis
    else:
        print("✅ No conflicts detected!")
        if not create_calendar_event:
            create_calendar_event = input("Create calendar event? (y/n): ").lower().strip() == 'y'
    
    # Create calendar event if requested
    if create_calendar_event:
        # Multi-person event support: create event for each attendee
        for attendee in request.required_attendees:
            calendar_name = attendee.value if hasattr(attendee, 'value') else str(attendee)
            print(f"Creating event for {calendar_name}...")
            scheduler.create_calendar_event(request, calendar_name=calendar_name)
        print("✅ Calendar events created for all attendees!")
    
    # Complete OmniFocus task if it exists
    complete_omnifocus_task(title, task_id)
    
    # Save reference information
    save_reference_info(request, analysis)
    
    return analysis

def suggest_alternative_times(scheduler: FamilyScheduler, request: ScheduleRequest):
    """Suggest alternative times for the scheduling request."""
    print("🕐 SUGGESTING ALTERNATIVE TIMES:")
    
    # Check different times on the same day
    alternative_times = [
        (request.target_date.replace(hour=8, minute=0), "8:00 AM"),
        (request.target_date.replace(hour=10, minute=0), "10:00 AM"),
        (request.target_date.replace(hour=14, minute=0), "2:00 PM"),
        (request.target_date.replace(hour=16, minute=0), "4:00 PM"),
        (request.target_date.replace(hour=18, minute=0), "6:00 PM"),
    ]
    
    for time, label in alternative_times:
        # Create temporary request with new time
        temp_request = ScheduleRequest(
            title=request.title,
            description=request.description,
            target_date=time,
            location=request.location,
            required_attendees=request.required_attendees,
            duration_minutes=request.duration_minutes
        )
        
        # Check for conflicts
        conflicts = scheduler._find_conflicts(temp_request)
        
        if not conflicts:
            print(f"  ✅ {label}: No conflicts")
        else:
            print(f"  ❌ {label}: {len(conflicts)} conflicts")
    
    print("\nTo reschedule, run the command again with a different time.")

def suggest_delegation(scheduler: FamilyScheduler, request: ScheduleRequest):
    """Suggest delegation options for the scheduling request."""
    print("👥 SUGGESTING DELEGATION OPTIONS:")
    
    # Check which family members are available
    available_members = []
    
    for member in FamilyMember:
        if member not in request.required_attendees:
            # Create temporary request with this member
            temp_request = ScheduleRequest(
                title=request.title,
                description=request.description,
                target_date=request.target_date,
                location=request.location,
                required_attendees=[member],
                duration_minutes=request.duration_minutes
            )
            
            conflicts = scheduler._find_conflicts(temp_request)
            
            if not conflicts:
                available_members.append(member)
                print(f"  ✅ {member.value}: Available")
            else:
                print(f"  ❌ {member.value}: {len(conflicts)} conflicts")
    
    if available_members:
        print(f"\n💡 Consider delegating to: {', '.join([m.value for m in available_members])}")
    else:
        print("\n❌ No family members available for delegation.")

def complete_omnifocus_task(task_title: str, task_id: Optional[str] = None):
    """Complete the corresponding OmniFocus task."""
    try:
        # Import the improved AppleScript client
        from omnifocus_api.apple_script_client import complete_task, set_task_note
        
        if task_id:
            # Use precise task ID matching with the improved function
            success = complete_task(task_id)
            if success:
                # Add scheduling note
                set_task_note(task_id, f"Scheduled via Family Scheduler - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                print("✅ OmniFocus task completed successfully")
            else:
                print("ℹ️  No matching OmniFocus task found")
        else:
            # For title-based matching, we need to find the task first
            # This is a fallback and less precise
            script = f'''
            tell application "OmniFocus"
                set theDoc to default document
                set theTask to first flattened task of theDoc whose name contains "{task_title}"
                if theTask is not missing value then
                    set taskId to id of theTask
                    return taskId
                else
                    return "NOT_FOUND"
                end if
            end tell
            '''
            
            import subprocess
            result = subprocess.run(['osascript', '-e', script], 
                                  capture_output=True, text=True)
            
            if result.returncode == 0 and result.stdout.strip() != "NOT_FOUND":
                found_task_id = result.stdout.strip()
                success = complete_task(found_task_id)
                if success:
                    set_task_note(found_task_id, f"Scheduled via Family Scheduler - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                    print("✅ OmniFocus task completed successfully")
                else:
                    print("ℹ️  No matching OmniFocus task found")
            else:
                print("ℹ️  No matching OmniFocus task found")
            
    except Exception as e:
        print(f"❌ Error completing OmniFocus task: {e}")

def save_reference_info(request: ScheduleRequest, analysis: Dict):
    """Save scheduling information to reference system."""
    reference_file = f"reference/docs/scheduling/{request.title.lower().replace(' ', '_')}_{request.target_date.strftime('%Y%m%d')}.md"
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(reference_file), exist_ok=True)
    
    content = f"""# {request.title}

## Event Details
- **Date**: {request.target_date.strftime('%Y-%m-%d %H:%I %p')}
- **Duration**: {request.duration_minutes} minutes
- **Location**: {request.location.name}
- **Address**: {request.location.address}
- **Attendees**: {', '.join([m.value for m in request.required_attendees])}
- **Priority**: {request.priority}

## Description
{request.description}

## Analysis Results
- **Calendar Events**: {analysis['calendar_events']}
- **Conflicts**: {analysis['conflicts']}
- **Solutions**: {analysis['solutions']}

## Conflicts
"""
    
    if analysis['conflict_details']:
        for conflict in analysis['conflict_details']:
            content += f"- **{conflict['severity'].upper()}**: {conflict['description']}\n"
    else:
        content += "- No conflicts detected\n"
    
    content += f"""
## Solutions
"""
    
    if analysis['solution_details']:
        for solution in analysis['solution_details']:
            solution_type = solution.get('solution_type', 'coordinate')
            content += f"- **{solution_type.title()}**: {solution['description']}\n"
            content += f"  - Impact: {solution.get('impact', 'low')}\n"
            coordination = solution.get('coordination_needed', [])
            if coordination:
                content += f"  - Coordination: {', '.join(coordination)}\n"
    else:
        content += "- No solutions needed\n"
    
    content += f"""
---
*Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""
    
    try:
        with open(reference_file, 'w') as f:
            f.write(content)
        print(f"✅ Saved reference information to {reference_file}")
    except Exception as e:
        print(f"❌ Error saving reference information: {e}")

def main():
    """Main function for command-line usage."""
    parser = argparse.ArgumentParser(description="Schedule family events with conflict analysis")
    parser.add_argument("title", help="Event title")
    parser.add_argument("description", help="Event description")
    parser.add_argument("date", help="Event date (YYYY-MM-DD)")
    parser.add_argument("location", help="Event location")
    parser.add_argument("attendees", nargs="+", help="Required attendees")
    parser.add_argument("--duration", type=int, default=60, help="Duration in minutes (default: 60)")
    parser.add_argument("--priority", choices=["low", "medium", "high", "critical"], 
                       default="medium", help="Event priority (default: medium)")
    parser.add_argument("--create-event", action="store_true", 
                       help="Automatically create calendar event")
    parser.add_argument("--task-id", help="Specific OmniFocus Task ID to complete after scheduling (for precise matching)")
    
    args = parser.parse_args()
    
    # Schedule the event
    analysis = schedule_family_event(
        title=args.title,
        description=args.description,
        date_str=args.date,
        location_name=args.location,
        attendees=args.attendees,
        duration_minutes=args.duration,
        priority=args.priority,
        create_calendar_event=args.create_event,
        task_id=getattr(args, 'task_id', None)
    )
    
    return analysis

if __name__ == "__main__":
    main() 