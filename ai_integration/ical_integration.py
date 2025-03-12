from typing import List, Dict, Optional
import icalendar
import recurring_ical_events
import datetime
import requests
from dataclasses import dataclass
from omnifocus_api.data_models import OmniFocusTask

@dataclass
class CalendarEvent:
    uid: str
    summary: str
    start: datetime.datetime
    end: datetime.datetime
    description: Optional[str] = None
    location: Optional[str] = None

def fetch_calendar_events(ical_url: str, start_date: datetime.datetime, end_date: datetime.datetime) -> List[CalendarEvent]:
    """Fetch events from an iCal calendar subscription."""
    response = requests.get(ical_url)
    calendar = icalendar.Calendar.from_ical(response.text)
    
    # Get all events including recurring ones
    events = recurring_ical_events.of(calendar).between(start_date, end_date)
    
    calendar_events = []
    for event in events:
        calendar_events.append(CalendarEvent(
            uid=str(event.get('uid', '')),
            summary=str(event.get('summary', '')),
            start=event.get('dtstart').dt,
            end=event.get('dtend').dt,
            description=str(event.get('description', '')),
            location=str(event.get('location', ''))
        ))
    
    return calendar_events

def verify_task_reality(task: OmniFocusTask, calendar_events: List[CalendarEvent]) -> bool:
    """
    Verify if a task corresponds to real events in the calendar.
    Returns True if the task is verified as real, False otherwise.
    """
    task_name_lower = task.name.lower()
    task_note_lower = task.note.lower() if task.note else ""
    
    for event in calendar_events:
        event_summary_lower = event.summary.lower()
        event_desc_lower = event.description.lower() if event.description else ""
        
        # Check for matching text in event summary or description
        if (task_name_lower in event_summary_lower or 
            task_name_lower in event_desc_lower or
            (task_note_lower and (task_note_lower in event_summary_lower or 
                                task_note_lower in event_desc_lower))):
            return True
    
    return False

def sync_with_calendar(tasks: List[OmniFocusTask], calendar_events: List[CalendarEvent]) -> Dict[str, bool]:
    """
    Sync OmniFocus tasks with calendar events to determine which are real.
    Returns a dictionary mapping task IDs to their reality status.
    """
    reality_status = {}
    
    for task in tasks:
        is_real = verify_task_reality(task, calendar_events)
        reality_status[task.id] = is_real
    
    return reality_status 