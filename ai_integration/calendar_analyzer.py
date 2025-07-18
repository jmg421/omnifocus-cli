#!/usr/bin/env python3
"""
Calendar Analyzer for OmniFocus Integration
Analyzes iCal calendars to identify scheduling conflicts and suggest solutions.
"""

import os
import sys
import json
import subprocess
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import icalendar
from dataclasses import dataclass
from pathlib import Path

# Add the omni-cli directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

@dataclass
class CalendarEvent:
    """Represents a calendar event with enhanced metadata."""
    title: str
    start_time: datetime
    end_time: datetime
    location: str
    calendar_name: str
    description: str = ""
    attendees: List[str] = None
    travel_time: int = 0  # minutes
    preparation_time: int = 0  # minutes
    
    def __post_init__(self):
        if self.attendees is None:
            self.attendees = []

@dataclass
class SchedulingConflict:
    """Represents a scheduling conflict between events."""
    event1: CalendarEvent
    event2: CalendarEvent
    conflict_type: str  # "overlap", "travel_time", "preparation_time"
    severity: str  # "critical", "warning", "info"
    description: str

@dataclass
class SchedulingSolution:
    """Represents a suggested solution to a scheduling conflict."""
    conflict: SchedulingConflict
    solution_type: str  # "reschedule", "delegate", "modify", "cancel"
    description: str
    impact: str  # "low", "medium", "high"
    implementation_steps: List[str]

class CalendarAnalyzer:
    """Analyzes calendar data for conflicts and suggests solutions."""
    
    def __init__(self):
        self.events: List[CalendarEvent] = []
        self.conflicts: List[SchedulingConflict] = []
        self.solutions: List[SchedulingSolution] = []
        
    def load_calendars(self, calendar_names: List[str] = None) -> List[CalendarEvent]:
        """Load events from specified calendars using AppleScript."""
        if calendar_names is None:
            # Default to common family calendars
            calendar_names = ["Family", "John", "Christina", "Grace", "Evan", "Weston"]
        
        events = []
        
        for calendar_name in calendar_names:
            try:
                # Use AppleScript to export calendar data
                script = f'''
                tell application "Calendar"
                    set cal to calendar "{calendar_name}"
                    set eventList to {{}}
                    
                    repeat with evt in events of cal
                        set eventInfo to {{
                            title:summary of evt,
                            start_date:start date of evt,
                            end_date:end date of evt,
                            location:location of evt,
                            description:description of evt,
                            attendees:attendees of evt
                        }}
                        set end of eventList to eventInfo
                    end repeat
                    
                    return eventList
                end tell
                '''
                
                result = subprocess.run(['osascript', '-e', script], 
                                      capture_output=True, text=True)
                
                if result.returncode == 0:
                    # Parse the AppleScript result (simplified for now)
                    # In practice, you'd need more sophisticated parsing
                    print(f"Loaded events from {calendar_name}")
                    
            except Exception as e:
                print(f"Error loading calendar {calendar_name}: {e}")
        
        return events
    
    def analyze_scheduling_conflicts(self, target_date: datetime) -> List[SchedulingConflict]:
        """Analyze scheduling conflicts for a specific date."""
        conflicts = []
        
        # Filter events for the target date
        day_events = [e for e in self.events 
                     if e.start_time.date() == target_date.date()]
        
        # Check for overlaps
        for i, event1 in enumerate(day_events):
            for event2 in day_events[i+1:]:
                if self._events_overlap(event1, event2):
                    conflicts.append(SchedulingConflict(
                        event1=event1,
                        event2=event2,
                        conflict_type="overlap",
                        severity="critical",
                        description=f"Events overlap: {event1.title} and {event2.title}"
                    ))
        
        # Check for travel time conflicts
        for i, event1 in enumerate(day_events):
            for event2 in day_events[i+1:]:
                if self._insufficient_travel_time(event1, event2):
                    conflicts.append(SchedulingConflict(
                        event1=event1,
                        event2=event2,
                        conflict_type="travel_time",
                        severity="warning",
                        description=f"Insufficient travel time between {event1.title} and {event2.title}"
                    ))
        
        return conflicts
    
    def suggest_solutions(self, conflicts: List[SchedulingConflict]) -> List[SchedulingSolution]:
        """Suggest solutions for scheduling conflicts."""
        solutions = []
        
        for conflict in conflicts:
            if conflict.conflict_type == "overlap":
                solutions.extend(self._suggest_overlap_solutions(conflict))
            elif conflict.conflict_type == "travel_time":
                solutions.extend(self._suggest_travel_solutions(conflict))
        
        return solutions
    
    def _events_overlap(self, event1: CalendarEvent, event2: CalendarEvent) -> bool:
        """Check if two events overlap in time."""
        return (event1.start_time < event2.end_time and 
                event2.start_time < event1.end_time)
    
    def _insufficient_travel_time(self, event1: CalendarEvent, event2: CalendarEvent) -> bool:
        """Check if there's insufficient travel time between events."""
        # Calculate travel time needed based on locations
        travel_time_needed = self._calculate_travel_time(event1.location, event2.location)
        
        # Check if there's enough time between events
        time_between = (event2.start_time - event1.end_time).total_seconds() / 60
        
        return time_between < travel_time_needed
    
    def _calculate_travel_time(self, location1: str, location2: str) -> int:
        """Calculate travel time between two locations (simplified)."""
        # This would integrate with Google Maps API or similar
        # For now, return estimated times based on known locations
        
        known_locations = {
            "Lewis Center, OH": {
                "Baltimore, OH": 90,  # ~1.5 hours
                "Crash Champions - 10130 Columbus Pike, Lewis Center, OH": 10,
                "Kroger": 15,
                "Mount Carmel Fitness Center": 20
            }
        }
        
        # Extract city/area from location strings
        loc1_area = self._extract_area(location1)
        loc2_area = self._extract_area(location2)
        
        if loc1_area in known_locations and loc2_area in known_locations[loc1_area]:
            return known_locations[loc1_area][loc2_area]
        
        return 30  # Default 30 minutes
    
    def _extract_area(self, location: str) -> str:
        """Extract area/city from location string."""
        if "Baltimore" in location:
            return "Baltimore, OH"
        elif "Lewis Center" in location:
            return "Lewis Center, OH"
        elif "Crash Champions" in location:
            return "Crash Champions - 10130 Columbus Pike, Lewis Center, OH"
        elif "Kroger" in location:
            return "Kroger"
        elif "Mount Carmel" in location:
            return "Mount Carmel Fitness Center"
        return location
    
    def _suggest_overlap_solutions(self, conflict: SchedulingConflict) -> List[SchedulingSolution]:
        """Suggest solutions for overlapping events."""
        solutions = []
        
        # Solution 1: Reschedule one event
        solutions.append(SchedulingSolution(
            conflict=conflict,
            solution_type="reschedule",
            description=f"Reschedule {conflict.event2.title} to avoid overlap",
            impact="medium",
            implementation_steps=[
                f"Check availability for {conflict.event2.title}",
                f"Propose alternative time",
                f"Update calendar"
            ]
        ))
        
        # Solution 2: Delegate attendance
        solutions.append(SchedulingSolution(
            conflict=conflict,
            solution_type="delegate",
            description=f"Have someone else attend {conflict.event1.title}",
            impact="low",
            implementation_steps=[
                f"Identify available family member",
                f"Coordinate handoff",
                f"Update calendar"
            ]
        ))
        
        return solutions
    
    def _suggest_travel_solutions(self, conflict: SchedulingConflict) -> List[SchedulingSolution]:
        """Suggest solutions for travel time conflicts."""
        solutions = []
        
        # Solution 1: Leave earlier
        solutions.append(SchedulingSolution(
            conflict=conflict,
            solution_type="modify",
            description=f"Leave earlier for {conflict.event2.title}",
            impact="low",
            implementation_steps=[
                f"Calculate required departure time",
                f"Update event start time",
                f"Notify attendees"
            ]
        ))
        
        # Solution 2: Use alternative transportation
        solutions.append(SchedulingSolution(
            conflict=conflict,
            solution_type="modify",
            description=f"Use alternative transportation for {conflict.event2.title}",
            impact="medium",
            implementation_steps=[
                f"Arrange ride sharing",
                f"Coordinate with family members",
                f"Update travel plans"
            ]
        ))
        
        return solutions
    
    def create_calendar_event(self, title: str, start_time: datetime, 
                            end_time: datetime, location: str, 
                            calendar_name: str = "Family") -> bool:
        """Create a new calendar event using AppleScript."""
        try:
            script = f'''
            tell application "Calendar"
                set cal to calendar "{calendar_name}"
                set newEvent to make new event at end of events of cal with properties {{
                    summary:"{title}",
                    start date:date "{start_time.strftime('%Y-%m-%d %H:%M:%S')}",
                    end date:date "{end_time.strftime('%Y-%m-%d %H:%M:%S')}",
                    location:"{location}"
                }}
                return id of newEvent
            end tell
            '''
            
            result = subprocess.run(['osascript', '-e', script], 
                                  capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"Created calendar event: {title}")
                return True
            else:
                print(f"Error creating calendar event: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"Error creating calendar event: {e}")
            return False

def analyze_scheduling_scenario(target_date: str, scenario_description: str) -> Dict:
    """Analyze a specific scheduling scenario and provide recommendations."""
    analyzer = CalendarAnalyzer()
    
    # Parse target date
    target_dt = datetime.strptime(target_date, "%Y-%m-%d")
    
    # Load calendars
    events = analyzer.load_calendars()
    
    # Analyze conflicts
    conflicts = analyzer.analyze_scheduling_conflicts(target_dt)
    
    # Generate solutions
    solutions = analyzer.suggest_solutions(conflicts)
    
    return {
        "target_date": target_date,
        "scenario": scenario_description,
        "events_found": len(events),
        "conflicts": len(conflicts),
        "solutions": len(solutions),
        "conflict_details": [
            {
                "type": c.conflict_type,
                "severity": c.severity,
                "description": c.description,
                "events": [c.event1.title, c.event2.title]
            }
            for c in conflicts
        ],
        "solution_details": [
            {
                "type": s.solution_type,
                "impact": s.impact,
                "description": s.description,
                "steps": s.implementation_steps
            }
            for s in solutions
        ]
    }

if __name__ == "__main__":
    # Example usage
    scenario = analyze_scheduling_scenario(
        "2025-07-19",  # Saturday
        "Evan car repair at Crash Champions while Grace has softball tournament in Baltimore"
    )
    
    print(json.dumps(scenario, indent=2, default=str)) 