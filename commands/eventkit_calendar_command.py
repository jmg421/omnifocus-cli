#!/usr/bin/env python3
"""
EventKit Calendar Command for OmniFocus CLI

This integrates the working EventKit solution that solved the calendar timeout issues.
EventKit provides fast, direct access to calendar data without AppleScript timeouts.
"""

import sys
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import json

# Add the parent directory to the path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

# Check if we have PyObjC EventKit installed
try:
    import objc
    from Foundation import NSDate
    from EventKit import EKEventStore, EKEntityTypeEvent, EKAuthorizationStatus
    EVENTKIT_AVAILABLE = True
except ImportError:
    EVENTKIT_AVAILABLE = False

class EventKitCalendarIntegration:
    """EventKit calendar integration for OmniFocus CLI."""
    
    def __init__(self):
        if not EVENTKIT_AVAILABLE:
            raise ImportError("EventKit framework not available. Install with: pip install pyobjc-framework-EventKit")
        
        self.event_store = EKEventStore.alloc().init()
        self.authorized = self._check_authorization()
        
        self.family_calendars = [
            "Family", "John", "Christina", "Grace", "Evan", "Weston",
            "UA Slammy Gold 14U", "Slammy Gold 14U", "Westerville Naturals 14U", 
            "Force Aquatics", "Sports", "OHS Run Brave Calendar", "Christina Gmail"
        ]
    
    def _check_authorization(self) -> bool:
        """Check current calendar authorization status."""
        try:
            if hasattr(self.event_store, 'authorizationStatusForEntityType_'):
                auth_status = self.event_store.authorizationStatusForEntityType_(EKEntityTypeEvent)
            elif hasattr(EKEventStore, 'authorizationStatusForEntityType_'):
                auth_status = EKEventStore.authorizationStatusForEntityType_(EKEntityTypeEvent)
            else:
                return False
            
            return auth_status == 3  # EKAuthorizationStatusAuthorized
        except:
            return False
    
    def get_events_next_24_hours(self) -> List[Dict]:
        """Get events for the next 24 hours."""
        if not self.authorized:
            return []
        
        now = datetime.now()
        tomorrow = now + timedelta(days=1)
        
        try:
            # Convert to NSDate
            start_date = NSDate.dateWithTimeIntervalSince1970_(now.timestamp())
            end_date = NSDate.dateWithTimeIntervalSince1970_(tomorrow.timestamp())
            
            # Get all calendars
            all_calendars = self.event_store.calendarsForEntityType_(EKEntityTypeEvent)
            
            # Create predicate for events
            predicate = self.event_store.predicateForEventsWithStartDate_endDate_calendars_(
                start_date, end_date, all_calendars
            )
            
            # Get events
            events = self.event_store.eventsMatchingPredicate_(predicate)
            
            # Convert to simple format
            result_events = []
            for event in events:
                try:
                    event_info = {
                        'title': str(event.title()) if event.title() else "No Title",
                        'start_date': datetime.fromtimestamp(event.startDate().timeIntervalSince1970()),
                        'end_date': datetime.fromtimestamp(event.endDate().timeIntervalSince1970()),
                        'calendar': str(event.calendar().title()) if event.calendar() and event.calendar().title() else "Unknown",
                        'location': str(event.location()) if event.location() else None,
                        'all_day': bool(event.isAllDay()) if hasattr(event, 'isAllDay') else False
                    }
                    result_events.append(event_info)
                except:
                    continue
            
            # Sort by start time
            result_events.sort(key=lambda x: x['start_date'])
            return result_events
            
        except Exception as e:
            print(f"❌ Error getting events: {e}")
            return []
    
    def get_family_calendar_events(self, days_ahead: int = 1) -> List[Dict]:
        """Get events from family calendars only."""
        if not self.authorized:
            return []
        
        now = datetime.now()
        future = now + timedelta(days=days_ahead)
        
        try:
            # Convert to NSDate
            start_date = NSDate.dateWithTimeIntervalSince1970_(now.timestamp())
            end_date = NSDate.dateWithTimeIntervalSince1970_(future.timestamp())
            
            # Get all calendars and filter for family ones
            all_calendars = self.event_store.calendarsForEntityType_(EKEntityTypeEvent)
            family_calendars = []
            
            for calendar in all_calendars:
                calendar_name = str(calendar.title())
                if calendar_name in self.family_calendars:
                    family_calendars.append(calendar)
            
            if not family_calendars:
                return []
            
            # Create predicate for events
            predicate = self.event_store.predicateForEventsWithStartDate_endDate_calendars_(
                start_date, end_date, family_calendars
            )
            
            # Get events
            events = self.event_store.eventsMatchingPredicate_(predicate)
            
            # Convert to simple format
            result_events = []
            for event in events:
                try:
                    event_info = {
                        'title': str(event.title()) if event.title() else "No Title",
                        'start_date': datetime.fromtimestamp(event.startDate().timeIntervalSince1970()),
                        'end_date': datetime.fromtimestamp(event.endDate().timeIntervalSince1970()),
                        'calendar': str(event.calendar().title()) if event.calendar() and event.calendar().title() else "Unknown",
                        'location': str(event.location()) if event.location() else None,
                        'all_day': bool(event.isAllDay()) if hasattr(event, 'isAllDay') else False
                    }
                    result_events.append(event_info)
                except:
                    continue
            
            # Sort by start time
            result_events.sort(key=lambda x: x['start_date'])
            return result_events
            
        except Exception as e:
            print(f"❌ Error getting family events: {e}")
            return []

def handle_eventkit_calendar_today(args):
    """Show today's events using EventKit."""
    print("📅 Today's Calendar Events (EventKit)")
    print("=" * 50)
    
    if not EVENTKIT_AVAILABLE:
        print("❌ EventKit not available")
        print("Install with: pip install pyobjc-framework-EventKit")
        return
    
    try:
        integration = EventKitCalendarIntegration()
        
        if not integration.authorized:
            print("❌ Not authorized to access calendars")
            print("💡 EventKit requires calendar permissions")
            return
        
        events = integration.get_events_next_24_hours()
        
        if not events:
            print("📅 No events found in next 24 hours")
            return
        
        print(f"📅 Found {len(events)} events in next 24 hours:")
        print()
        
        # Group by date
        today = datetime.now().date()
        tomorrow = today + timedelta(days=1)
        
        today_events = [e for e in events if e['start_date'].date() == today]
        tomorrow_events = [e for e in events if e['start_date'].date() == tomorrow]
        
        if today_events:
            print(f"📅 Today ({today.strftime('%B %d, %Y')}):")
            for event in today_events:
                time_str = "All day" if event['all_day'] else event['start_date'].strftime('%I:%M %p')
                print(f"  • {time_str} - {event['title']} ({event['calendar']})")
                if event['location']:
                    print(f"    📍 {event['location']}")
            print()
        
        if tomorrow_events:
            print(f"📅 Tomorrow ({tomorrow.strftime('%B %d, %Y')}):")
            for event in tomorrow_events:
                time_str = "All day" if event['all_day'] else event['start_date'].strftime('%I:%M %p')
                print(f"  • {time_str} - {event['title']} ({event['calendar']})")
                if event['location']:
                    print(f"    📍 {event['location']}")
        
    except Exception as e:
        print(f"❌ Error: {e}")

def handle_eventkit_family_events(args):
    """Show family calendar events using EventKit."""
    print("👨‍👩‍👧‍👦 Family Calendar Events (EventKit)")
    print("=" * 50)
    
    if not EVENTKIT_AVAILABLE:
        print("❌ EventKit not available")
        print("Install with: pip install pyobjc-framework-EventKit")
        return
    
    try:
        integration = EventKitCalendarIntegration()
        
        if not integration.authorized:
            print("❌ Not authorized to access calendars")
            return
        
        # Get events for next 3 days for family
        events = integration.get_family_calendar_events(3)
        
        if not events:
            print("📅 No family events found in next 3 days")
            return
        
        print(f"📅 Found {len(events)} family events in next 3 days:")
        print()
        
        # Group by calendar
        events_by_calendar = {}
        for event in events:
            cal_name = event['calendar']
            if cal_name not in events_by_calendar:
                events_by_calendar[cal_name] = []
            events_by_calendar[cal_name].append(event)
        
        for calendar_name in sorted(events_by_calendar.keys()):
            if calendar_name in integration.family_calendars:
                cal_events = events_by_calendar[calendar_name]
                print(f"📅 {calendar_name} Calendar ({len(cal_events)} events):")
                
                for event in cal_events[:5]:  # Show first 5 per calendar
                    date_str = event['start_date'].strftime('%m/%d')
                    time_str = "All day" if event['all_day'] else event['start_date'].strftime('%I:%M %p')
                    print(f"  • {date_str} {time_str} - {event['title']}")
                    if event['location']:
                        print(f"    📍 {event['location']}")
                
                if len(cal_events) > 5:
                    print(f"    ... and {len(cal_events) - 5} more events")
                print()
        
    except Exception as e:
        print(f"❌ Error: {e}")

def handle_eventkit_calendar_conflicts(args):
    """Check for scheduling conflicts using EventKit."""
    print("⚠️  Calendar Conflict Check (EventKit)")
    print("=" * 50)
    
    if not EVENTKIT_AVAILABLE:
        print("❌ EventKit not available")
        return
    
    # Parse time arguments
    try:
        start_time = datetime.strptime(args.start_time, '%Y-%m-%d %H:%M')
        end_time = datetime.strptime(args.end_time, '%Y-%m-%d %H:%M')
    except ValueError:
        print("❌ Invalid time format. Use YYYY-MM-DD HH:MM")
        return
    
    try:
        integration = EventKitCalendarIntegration()
        
        if not integration.authorized:
            print("❌ Not authorized to access calendars")
            return
        
        # Get events in the specified time range
        events = integration.get_family_calendar_events(7)  # Look ahead 7 days
        
        conflicts = []
        for event in events:
            # Check if event overlaps with requested time
            event_start = event['start_date']
            event_end = event['end_date']
            
            # Event overlaps if: event_start < end_time AND event_end > start_time
            if event_start < end_time and event_end > start_time:
                conflicts.append(event)
        
        if conflicts:
            print(f"⚠️  Found {len(conflicts)} scheduling conflicts:")
            for event in conflicts:
                print(f"  • {event['title']} ({event['calendar']})")
                print(f"    {event['start_date'].strftime('%Y-%m-%d %I:%M %p')} - {event['end_date'].strftime('%I:%M %p')}")
                if event['location']:
                    print(f"    📍 {event['location']}")
                print()
        else:
            print("✅ No scheduling conflicts found")
            print(f"Time slot {start_time.strftime('%Y-%m-%d %I:%M %p')} - {end_time.strftime('%I:%M %p')} is available")
        
    except Exception as e:
        print(f"❌ Error: {e}")

# Integration functions for the main CLI
def eventkit_calendar_today():
    """Quick today events function for CLI integration."""
    args = type('Args', (), {})
    handle_eventkit_calendar_today(args)

def eventkit_family_events():
    """Family events function for CLI integration.""" 
    args = type('Args', (), {})
    handle_eventkit_family_events(args) 