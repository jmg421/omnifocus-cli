#!/usr/bin/env python3
"""
icalBuddy Integration for OmniFocus CLI
Provides calendar integration using icalBuddy for task reality checking and scheduling.
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
    """Represents a calendar event from icalBuddy."""
    title: str
    datetime: str
    location: Optional[str] = None
    notes: Optional[str] = None
    calendar: Optional[str] = None
    uid: Optional[str] = None

class IcalBuddyIntegration:
    """Integration class for icalBuddy calendar access."""
    
    def __init__(self):
        self.family_calendars = [
            "Family", "Family Member 1", "Family Member 2", "Family Member 3", "Family Member 4", "Family Member 5",
            "Sports Team 1", "Sports Team 2", "Sports Team 3",
            "Aquatics", "Sports", "Family Gmail"
        ]
    
    def check_icalbuddy_available(self) -> bool:
        """Check if icalBuddy is available and working."""
        try:
            result = subprocess.run(['icalBuddy', 'calendars'], 
                                  capture_output=True, text=True, timeout=10)
            return result.returncode == 0 and result.stdout.strip() != ""
        except Exception:
            return False
    
    def get_calendars(self) -> List[str]:
        """Get list of available calendars."""
        try:
            result = subprocess.run(['icalBuddy', 'calendars'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                return [cal.strip() for cal in result.stdout.strip().split('\n') if cal.strip()]
            return []
        except Exception as e:
            print(f"Error getting calendars: {e}")
            return []
    
    def get_events_today(self, calendar_names: Optional[List[str]] = None) -> List[CalendarEvent]:
        """Get events for today from specified calendars."""
        if calendar_names is None:
            calendar_names = self.family_calendars
        
        events = []
        for calendar in calendar_names:
            try:
                # Use icalBuddy to get events for today from this calendar
                cmd = ['icalBuddy', '-ic', calendar, '-iep', 'title,datetime,location,notes', 'eventsToday']
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                
                if result.returncode == 0 and result.stdout.strip():
                    # Parse the output (icalBuddy format)
                    lines = result.stdout.strip().split('\n')
                    current_event = None
                    
                    for line in lines:
                        line = line.strip()
                        if line and not line.startswith('•'):
                            # This is a new event
                            if current_event:
                                events.append(current_event)
                            current_event = CalendarEvent(title=line, datetime="", calendar=calendar)
                        elif line.startswith('•') and current_event:
                            # This is a property of the current event
                            if 'datetime:' in line:
                                current_event.datetime = line.split('datetime:', 1)[1].strip()
                            elif 'location:' in line:
                                current_event.location = line.split('location:', 1)[1].strip()
                            elif 'notes:' in line:
                                current_event.notes = line.split('notes:', 1)[1].strip()
                    
                    if current_event:
                        events.append(current_event)
                        
            except Exception as e:
                print(f"Error getting events from {calendar}: {e}")
                continue
        
        return events
    
    def get_events_in_range(self, start_date: datetime, end_date: datetime, 
                           calendar_names: Optional[List[str]] = None) -> List[CalendarEvent]:
        """Get events in a date range from specified calendars."""
        if calendar_names is None:
            calendar_names = self.family_calendars
        
        # Format dates for icalBuddy
        start_str = start_date.strftime('%Y-%m-%d %H:%M:%S')
        end_str = end_date.strftime('%Y-%m-%d %H:%M:%S')
        
        events = []
        for calendar in calendar_names:
            try:
                cmd = [
                    'icalBuddy', '-ic', calendar, 
                    '-iep', 'title,datetime,location,notes',
                    f'eventsFrom:{start_str} to:{end_str}'
                ]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                
                if result.returncode == 0 and result.stdout.strip():
                    # Parse similar to get_events_today
                    lines = result.stdout.strip().split('\n')
                    current_event = None
                    
                    for line in lines:
                        line = line.strip()
                        if line and not line.startswith('•'):
                            if current_event:
                                events.append(current_event)
                            current_event = CalendarEvent(title=line, datetime="", calendar=calendar)
                        elif line.startswith('•') and current_event:
                            if 'datetime:' in line:
                                current_event.datetime = line.split('datetime:', 1)[1].strip()
                            elif 'location:' in line:
                                current_event.location = line.split('location:', 1)[1].strip()
                            elif 'notes:' in line:
                                current_event.notes = line.split('notes:', 1)[1].strip()
                    
                    if current_event:
                        events.append(current_event)
                        
            except Exception as e:
                print(f"Error getting events from {calendar}: {e}")
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
            # Parse event datetime and check for overlap
            try:
                event_start = datetime.strptime(event.datetime, '%Y-%m-%d %H:%M:%S')
                # Assume 1-hour duration if not specified
                event_end = event_start + timedelta(hours=1)
                
                # Check for overlap
                if (event_start < end_time and event_end > start_time):
                    conflicts.append(event)
            except ValueError:
                # Skip events with unparseable dates
                continue
        
        return conflicts

def handle_icalbuddy_test(args):
    """Test icalBuddy integration."""
    integration = IcalBuddyIntegration()
    
    print("🔍 Testing icalBuddy Integration")
    print("=" * 40)
    
    # Check if icalBuddy is available
    if not integration.check_icalbuddy_available():
        print("❌ icalBuddy is not available or not working")
        print("Please ensure icalBuddy has Full Disk Access permissions")
        return
    
    print("✅ icalBuddy is available")
    
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
            if event.datetime:
                print(f"    Time: {event.datetime}")
            if event.location:
                print(f"    Location: {event.location}")
    else:
        print("  No events found for today")

def handle_icalbuddy_verify(args):
    """Verify task reality against calendar events."""
    integration = IcalBuddyIntegration()
    
    if not integration.check_icalbuddy_available():
        print("❌ icalBuddy is not available")
        return
    
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
            if event.datetime:
                print(f"    Time: {event.datetime}")
            if event.location:
                print(f"    Location: {event.location}")

def handle_icalbuddy_conflicts(args):
    """Check for scheduling conflicts."""
    integration = IcalBuddyIntegration()
    
    if not integration.check_icalbuddy_available():
        print("❌ icalBuddy is not available")
        return
    
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
            if event.datetime:
                print(f"    Time: {event.datetime}")
            if event.location:
                print(f"    Location: {event.location}")
    else:
        print("✅ No scheduling conflicts found") 