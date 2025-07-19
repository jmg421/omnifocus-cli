#!/usr/bin/env python3
"""
AppleScript Calendar Integration for OmniFocus CLI
Provides calendar integration using AppleScript for task reality checking and scheduling.
This should work without special permissions since AppleScript already has Calendar access.
"""

import subprocess
import json
import sys
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from dataclasses import dataclass

# Add the omni-cli directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

@dataclass
class CalendarEvent:
    """Represents a calendar event from AppleScript."""
    title: str
    start_date: str
    end_date: str
    location: Optional[str] = None
    notes: Optional[str] = None
    calendar: Optional[str] = None
    uid: Optional[str] = None

class AppleScriptCalendarIntegration:
    """Integration class for AppleScript calendar access."""
    
    def __init__(self):
        self.family_calendars = [
            "Family", "John", "Christina", "Grace", "Evan", "Weston",
            "UA Slammy Gold 14U", "Slammy Gold 14U", "Westerville Naturals 14U",
            "Force Aquatics", "Sports", "Christina Gmail"
        ]
    
    def get_calendars(self) -> List[str]:
        """Get list of available calendars using AppleScript."""
        try:
            script = '''
            tell application "Calendar"
                set calendarNames to {}
                repeat with cal in calendars
                    set end of calendarNames to name of cal
                end repeat
                return calendarNames
            end tell
            '''
            
            result = subprocess.run(['osascript', '-e', script], 
                                  capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                calendars = result.stdout.strip().split(', ')
                return [cal.strip() for cal in calendars if cal.strip()]
            return []
        except Exception as e:
            print(f"Error getting calendars: {e}")
            return []
    
    def get_events_today(self, calendar_names: Optional[List[str]] = None) -> List[CalendarEvent]:
        """Get events for today from specified calendars using AppleScript."""
        if calendar_names is None:
            calendar_names = self.family_calendars
        
        events = []
        today = datetime.now().strftime('%Y-%m-%d')
        
        for calendar in calendar_names:
            try:
                script = f'''
                tell application "Calendar"
                    set cal to calendar "{calendar}"
                    set eventList to {{}}
                    set todayDate to date "{today}"
                    
                    repeat with evt in events of cal
                        set startDate to start date of evt
                        
                        -- Check if event is today
                        if (year of startDate = year of todayDate and month of startDate = month of todayDate and day of startDate = day of todayDate) then
                            set eventInfo to {{
                                title:summary of evt,
                                start_date:(start date of evt as string),
                                end_date:(end date of evt as string),
                                location:location of evt,
                                notes:description of evt,
                                calendar:"{calendar}"
                            }}
                            set end of eventList to eventInfo
                        end if
                    end repeat
                    
                    return eventList
                end tell
                '''
                
                result = subprocess.run(['osascript', '-e', script], 
                                      capture_output=True, text=True, timeout=10)
                
                if result.returncode == 0 and result.stdout.strip():
                    # Parse the AppleScript result
                    # This is a simplified parser - in practice you'd need more sophisticated parsing
                    lines = result.stdout.strip().split('\n')
                    for line in lines:
                        if line.strip() and 'title:' in line:
                            # Extract event info (simplified)
                            title = line.split('title:', 1)[1].strip() if 'title:' in line else "Unknown"
                            events.append(CalendarEvent(
                                title=title,
                                start_date="",
                                end_date="",
                                calendar=calendar
                            ))
                        
            except Exception as e:
                print(f"Error getting events from {calendar}: {e}")
                continue
        
        return events
    
    def get_events_in_range(self, start_date: datetime, end_date: datetime, 
                           calendar_names: Optional[List[str]] = None) -> List[CalendarEvent]:
        """Get events in a date range from specified calendars using AppleScript."""
        if calendar_names is None:
            calendar_names = self.family_calendars
        
        events = []
        start_str = start_date.strftime('%B %d, %Y at %I:%M %p')
        end_str = end_date.strftime('%B %d, %Y at %I:%M %p')
        
        print(f"🔍 Querying {len(calendar_names)} calendars for events between {start_str} and {end_str}")
        
        for calendar in calendar_names:
            try:
                print(f"  📅 Checking {calendar} calendar...")
                
                # Use the actual date range parameters
                script = f'''
                tell application "Calendar"
                    set cal to calendar "{calendar}"
                    set eventList to {{}}
                    set eventCount to 0
                    
                    -- Convert input dates to AppleScript date objects
                    set startDate to date "{start_date.strftime('%Y-%m-%d %H:%M:%S')}"
                    set endDate to date "{end_date.strftime('%Y-%m-%d %H:%M:%S')}"
                    
                    repeat with evt in events of cal
                        set evtStart to start date of evt
                        
                        -- Check if event starts within the specified date range
                        if (evtStart ≥ startDate and evtStart ≤ endDate) then
                            set eventCount to eventCount + 1
                            
                            -- Limit to first 50 events to avoid timeout
                            if eventCount ≤ 50 then
                                set eventInfo to {{
                                    title:summary of evt,
                                    start_date:(start date of evt as string),
                                    end_date:(end date of evt as string),
                                    location:location of evt,
                                    notes:description of evt,
                                    calendar:"{calendar}"
                                }}
                                set end of eventList to eventInfo
                            end if
                        end if
                    end repeat
                    
                    return {{eventCount, eventList}}
                end tell
                '''
                
                result = subprocess.run(['osascript', '-e', script], 
                                      capture_output=True, text=True, timeout=15)
                
                if result.returncode == 0 and result.stdout.strip():
                    print(f"    ✅ Found events in {calendar}")
                    
                    # Parse the AppleScript result
                    output = result.stdout.strip()
                    lines = output.split('\n')
                    
                    # Look for event information
                    current_event = {}
                    for line in lines:
                        line = line.strip()
                        if 'title:' in line:
                            if current_event:
                                # Save previous event
                                events.append(CalendarEvent(
                                    title=current_event.get('title', 'Unknown'),
                                    start_date=current_event.get('start_date', ''),
                                    end_date=current_event.get('end_date', ''),
                                    location=current_event.get('location', ''),
                                    notes=current_event.get('notes', ''),
                                    calendar=calendar
                                ))
                            
                            # Start new event
                            current_event = {'title': line.split('title:', 1)[1].strip()}
                        elif 'start_date:' in line:
                            current_event['start_date'] = line.split('start_date:', 1)[1].strip()
                        elif 'end_date:' in line:
                            current_event['end_date'] = line.split('end_date:', 1)[1].strip()
                        elif 'location:' in line:
                            current_event['location'] = line.split('location:', 1)[1].strip()
                        elif 'notes:' in line:
                            current_event['notes'] = line.split('notes:', 1)[1].strip()
                    
                    # Don't forget the last event
                    if current_event:
                        events.append(CalendarEvent(
                            title=current_event.get('title', 'Unknown'),
                            start_date=current_event.get('start_date', ''),
                            end_date=current_event.get('end_date', ''),
                            location=current_event.get('location', ''),
                            notes=current_event.get('notes', ''),
                            calendar=calendar
                        ))
                else:
                    print(f"    ⭕ No events found in {calendar}")
                        
            except subprocess.TimeoutExpired:
                print(f"    ⏰ Timeout checking {calendar} calendar")
                continue
            except Exception as e:
                print(f"    ❌ Error checking {calendar}: {e}")
                continue
        
        return events
    
    def verify_task_reality(self, task_name: str, task_notes: Optional[str] = None) -> bool:
        """Verify if a task corresponds to real calendar events."""
        events = self.get_events_today()
        task_name_lower = task_name.lower()
        task_notes_lower = (task_notes or "").lower()
        
        for event in events:
            event_title_lower = event.title.lower()
            event_notes_lower = (event.notes or "").lower()
            
            # Check for matching text in event title or notes
            if (task_name_lower in event_title_lower or 
                task_name_lower in event_notes_lower or
                (task_notes_lower and (task_notes_lower in event_title_lower or 
                                     task_notes_lower in event_notes_lower))):
                return True
        
        return False
    
    def check_scheduling_conflicts(self, start_time: datetime, end_time: datetime,
                                 calendar_names: Optional[List[str]] = None) -> List[CalendarEvent]:
        """Check for scheduling conflicts in a time range."""
        events = self.get_events_in_range(start_time, end_time, calendar_names)
        conflicts = []
        
        for event in events:
            # For now, assume any event in the range is a conflict
            # In a full implementation, you'd parse the dates and check for actual overlap
            conflicts.append(event)
        
        return conflicts

def handle_applescript_calendar_test(args):
    """Test AppleScript calendar integration."""
    integration = AppleScriptCalendarIntegration()
    
    print("🔍 Testing AppleScript Calendar Integration")
    print("=" * 50)
    
    # Get available calendars
    calendars = integration.get_calendars()
    print(f"📅 Available calendars: {len(calendars)}")
    for cal in calendars:
        print(f"  • {cal}")
    
    # Get today's events
    print("\n📅 Today's events:")
    events = integration.get_events_today()
    if events:
        for event in events:
            print(f"  • {event.title} ({event.calendar})")
            if event.start_date:
                print(f"    Time: {event.start_date}")
            if event.location:
                print(f"    Location: {event.location}")
    else:
        print("  No events found for today")

def handle_applescript_calendar_verify(args):
    """Verify task reality against calendar events."""
    integration = AppleScriptCalendarIntegration()
    
    task_name = args.task_name
    task_notes = getattr(args, 'notes', None)
    
    print(f"🔍 Verifying task reality: {task_name}")
    print("=" * 50)
    
    is_real = integration.verify_task_reality(task_name, task_notes)
    
    if is_real:
        print("✅ Task appears to be REAL (matches calendar events)")
    else:
        print("❌ Task appears to be NOT REAL (no matching calendar events)")
    
    # Show matching events
    events = integration.get_events_today()
    matching_events = []
    
    for event in events:
        if (task_name.lower() in event.title.lower() or
            (task_notes and task_notes.lower() in event.title.lower())):
            matching_events.append(event)
    
    if matching_events:
        print(f"\n📅 Found {len(matching_events)} potentially matching events:")
        for event in matching_events:
            print(f"  • {event.title} ({event.calendar})")
            if event.start_date:
                print(f"    Time: {event.start_date}")
            if event.location:
                print(f"    Location: {event.location}")

def handle_applescript_calendar_conflicts(args):
    """Check for scheduling conflicts."""
    integration = AppleScriptCalendarIntegration()
    
    start_time = datetime.strptime(args.start_time, '%Y-%m-%d %H:%M')
    end_time = datetime.strptime(args.end_time, '%Y-%m-%d %H:%M')
    
    print(f"🔍 Checking scheduling conflicts")
    print(f"Time range: {start_time} to {end_time}")
    print("=" * 50)
    
    conflicts = integration.check_scheduling_conflicts(start_time, end_time)
    
    if conflicts:
        print(f"⚠️  Found {len(conflicts)} scheduling conflicts:")
        for event in conflicts:
            print(f"  • {event.title} ({event.calendar})")
            if event.start_date:
                print(f"    Time: {event.start_date}")
            if event.location:
                print(f"    Location: {event.location}")
    else:
        print("✅ No scheduling conflicts found")

def handle_applescript_calendar_events(args):
    """Get events for a specific time range."""
    integration = AppleScriptCalendarIntegration()
    
    # Handle both date-only and date-time formats
    def parse_datetime_flexible(dt_str):
        try:
            return datetime.strptime(dt_str, '%Y-%m-%d %H:%M')
        except ValueError:
            try:
                return datetime.strptime(dt_str, '%Y-%m-%d')
            except ValueError:
                raise ValueError(f"Invalid date format: {dt_str}. Use YYYY-MM-DD or YYYY-MM-DD HH:MM")
    
    start_time = parse_datetime_flexible(args.start_time)
    end_time = parse_datetime_flexible(args.end_time)
    
    print(f"📅 Getting calendar events")
    print(f"Time range: {start_time} to {end_time}")
    print("=" * 50)
    
    events = integration.get_events_in_range(start_time, end_time)
    
    if events:
        print(f"✅ Found {len(events)} events:")
        # Sort events by calendar and title for better organization
        events.sort(key=lambda x: (x.calendar, x.title))
        
        current_calendar = None
        for event in events:
            if event.calendar != current_calendar:
                current_calendar = event.calendar
                print(f"\n📅 {current_calendar} Calendar:")
            
            print(f"  • {event.title}")
            if event.start_date:
                print(f"    Time: {event.start_date}")
            if event.location:
                print(f"    Location: {event.location}")
            if event.notes:
                print(f"    Notes: {event.notes}")
    else:
        print("✅ No events found in the specified time range") 