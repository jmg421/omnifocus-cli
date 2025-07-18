#!/usr/bin/env python3
"""
Family Scheduler - Generic Family Logistics Planning
Handles complex scheduling scenarios involving multiple family members, transportation, and calendar conflicts.
"""

import os
import sys
import json
import subprocess
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple, Set
from dataclasses import dataclass
from enum import Enum

# Add the omni-cli directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

class TransportationMode(Enum):
    WALK = "walk"
    DRIVE = "drive"
    RIDE_SHARE = "ride_share"
    PUBLIC_TRANSIT = "public_transit"
    BIKE = "bike"

class FamilyMember(Enum):
    JOHN = "John"
    CHRISTINA = "Christina"
    EVAN = "Evan"
    GRACE = "Grace"
    WESTON = "Weston"

@dataclass
class Location:
    """Represents a location with metadata."""
    name: str
    address: str
    coordinates: Optional[Tuple[float, float]] = None
    travel_time_from_home: int = 0  # minutes
    notes: str = ""

@dataclass
class ScheduleRequest:
    """Represents a scheduling request."""
    title: str
    description: str
    target_date: datetime
    location: Location
    required_attendees: List[FamilyMember]
    optional_attendees: List[FamilyMember] = None
    duration_minutes: int = 60
    priority: str = "medium"  # low, medium, high, critical
    transportation_needed: bool = True
    preparation_time_minutes: int = 0
    
    def __post_init__(self):
        if self.optional_attendees is None:
            self.optional_attendees = []

@dataclass
class CalendarEvent:
    """Enhanced calendar event with family context."""
    title: str
    start_time: datetime
    end_time: datetime
    location: str
    calendar_name: str
    attendees: List[str] = None
    description: str = ""
    travel_time: int = 0
    preparation_time: int = 0
    
    def __post_init__(self):
        if self.attendees is None:
            self.attendees = []

@dataclass
class SchedulingConflict:
    """Represents a scheduling conflict."""
    event1: CalendarEvent
    event2: CalendarEvent
    conflict_type: str  # "overlap", "travel_time", "transportation", "preparation"
    severity: str  # "critical", "warning", "info"
    description: str
    affected_family_members: List[FamilyMember]

@dataclass
class SchedulingSolution:
    """Represents a solution to a scheduling conflict."""
    conflict: SchedulingConflict
    solution_type: str  # "reschedule", "delegate", "modify", "cancel", "coordinate"
    description: str
    impact: str  # "low", "medium", "high"
    implementation_steps: List[str]
    required_coordination: List[FamilyMember]

class FamilyScheduler:
    """Generic family scheduling system."""
    
    def __init__(self):
        self.family_members = {
            FamilyMember.JOHN: {
                "name": "John",
                "calendar": "John",
                "transportation": ["drive", "walk"],
                "availability": "flexible"
            },
            FamilyMember.CHRISTINA: {
                "name": "Christina", 
                "calendar": "Christina",
                "transportation": ["drive", "walk"],
                "availability": "flexible"
            },
            FamilyMember.EVAN: {
                "name": "Evan",
                "calendar": "Evan", 
                "transportation": ["drive", "walk"],
                "availability": "work_schedule"
            },
            FamilyMember.GRACE: {
                "name": "Grace",
                "calendar": "Grace",
                "transportation": ["ride"],
                "availability": "dependent"
            },
            FamilyMember.WESTON: {
                "name": "Weston",
                "calendar": "Weston",
                "transportation": ["ride"],
                "availability": "dependent"
            }
        }
        
        self.known_locations = {
            "home": Location(
                name="Home",
                address="5716 Ludington Drive, Lewis Center, OH 43035",
                travel_time_from_home=0
            ),
            "crash_champions": Location(
                name="Crash Champions",
                address="10130 Columbus Pike, Lewis Center, OH 43035", 
                travel_time_from_home=10
            ),
            "kroger": Location(
                name="Kroger",
                address="Lewis Center, OH",
                travel_time_from_home=15
            ),
            "baltimore_softball": Location(
                name="Baltimore Softball Complex",
                address="1101 N Romulus St, Baltimore, OH",
                travel_time_from_home=90
            ),
            "mount_carmel": Location(
                name="Mount Carmel Fitness Center",
                address="Mount Carmel Fitness Center",
                travel_time_from_home=20
            )
        }
        
        self.events: List[CalendarEvent] = []
        self.conflicts: List[SchedulingConflict] = []
        self.solutions: List[SchedulingSolution] = []
    
    def load_calendar_data(self, target_date: datetime) -> List[CalendarEvent]:
        """Load calendar data for all family members on target date."""
        events = []
        
        for member in FamilyMember:
            member_info = self.family_members[member]
            calendar_name = member_info["calendar"]
            
            try:
                # Use AppleScript to get calendar events
                script = f'''
                tell application "Calendar"
                    set cal to calendar "{calendar_name}"
                    set eventList to {{}}
                    
                    repeat with evt in events of cal
                        set startDate to start date of evt
                        set endDate to end date of evt
                        
                        -- Check if event is on target date
                        if (year of startDate = {target_date.year} and month of startDate = {target_date.month} and day of startDate = {target_date.day}) then
                            set eventInfo to {{
                                title:summary of evt,
                                start_date:startDate,
                                end_date:endDate,
                                location:location of evt,
                                description:description of evt,
                                calendar_name:"{calendar_name}"
                            }}
                            set end of eventList to eventInfo
                        end if
                    end repeat
                    
                    return eventList
                end tell
                '''
                
                result = subprocess.run(['osascript', '-e', script], 
                                      capture_output=True, text=True)
                
                if result.returncode == 0:
                    # Parse AppleScript result (simplified)
                    print(f"Loaded events from {calendar_name}")
                    # In practice, you'd parse the actual AppleScript result
                    
            except Exception as e:
                print(f"Error loading calendar {calendar_name}: {e}")
        
        return events
    
    def analyze_scheduling_request(self, request: ScheduleRequest) -> Dict:
        """Analyze a scheduling request and provide recommendations."""
        print(f"🔍 Analyzing scheduling request: {request.title}")
        print("=" * 60)
        
        # Load calendar data
        self.events = self.load_calendar_data(request.target_date)
        
        # Analyze conflicts
        self.conflicts = self._find_conflicts(request)
        
        # Generate solutions
        self.solutions = self._generate_solutions(request)
        
        # Create comprehensive analysis
        analysis = {
            "request": {
                "title": request.title,
                "date": request.target_date.strftime("%Y-%m-%d"),
                "location": request.location.name,
                "attendees": [m.value for m in request.required_attendees],
                "duration": request.duration_minutes
            },
            "calendar_events": len(self.events),
            "conflicts": len(self.conflicts),
            "solutions": len(self.solutions),
            "conflict_details": [
                {
                    "type": c.conflict_type,
                    "severity": c.severity,
                    "description": c.description,
                    "affected_members": [m.value for m in c.affected_family_members]
                }
                for c in self.conflicts
            ],
            "solution_details": [
                {
                    "type": s.solution_type,
                    "impact": s.impact,
                    "description": s.description,
                    "steps": s.implementation_steps,
                    "coordination_needed": [m.value for m in s.required_coordination]
                }
                for s in self.solutions
            ]
        }
        
        return analysis
    
    def _find_conflicts(self, request: ScheduleRequest) -> List[SchedulingConflict]:
        """Find scheduling conflicts for the request."""
        conflicts = []
        
        # Check for time overlaps with required attendees
        for event in self.events:
            for member in request.required_attendees:
                if self._is_member_involved(event, member):
                    if self._events_overlap(request, event):
                        conflicts.append(SchedulingConflict(
                            event1=CalendarEvent(
                                title=request.title,
                                start_time=request.target_date,
                                end_time=request.target_date + timedelta(minutes=request.duration_minutes),
                                location=request.location.name,
                                calendar_name="Request"
                            ),
                            event2=event,
                            conflict_type="overlap",
                            severity="critical",
                            description=f"Time conflict: {request.title} overlaps with {event.title}",
                            affected_family_members=[member]
                        ))
        
        # Check for transportation conflicts
        if request.transportation_needed:
            transportation_conflicts = self._check_transportation_conflicts(request)
            conflicts.extend(transportation_conflicts)
        
        return conflicts
    
    def _is_member_involved(self, event: CalendarEvent, member: FamilyMember) -> bool:
        """Check if a family member is involved in an event."""
        member_info = self.family_members[member]
        return event.calendar_name == member_info["calendar"]
    
    def _events_overlap(self, request: ScheduleRequest, event: CalendarEvent) -> bool:
        """Check if request overlaps with existing event."""
        request_start = request.target_date
        request_end = request_start + timedelta(minutes=request.duration_minutes)
        
        return (request_start < event.end_time and event.start_time < request_end)
    
    def _check_transportation_conflicts(self, request: ScheduleRequest) -> List[SchedulingConflict]:
        """Check for transportation-related conflicts."""
        conflicts = []
        
        # Check if required attendees have transportation conflicts
        for member in request.required_attendees:
            member_info = self.family_members[member]
            
            # Check if member has other events that require transportation
            for event in self.events:
                if self._is_member_involved(event, member):
                    if self._locations_require_transportation(event.location, request.location.name):
                        # Check if there's insufficient time between events
                        if self._insufficient_travel_time(event, request):
                            conflicts.append(SchedulingConflict(
                                event1=CalendarEvent(
                                    title=request.title,
                                    start_time=request.target_date,
                                    end_time=request.target_date + timedelta(minutes=request.duration_minutes),
                                    location=request.location.name,
                                    calendar_name="Request"
                                ),
                                event2=event,
                                conflict_type="transportation",
                                severity="warning",
                                description=f"Transportation conflict: {member.value} needs to be at {event.location} and {request.location.name}",
                                affected_family_members=[member]
                            ))
        
        return conflicts
    
    def _locations_require_transportation(self, loc1: str, loc2: str) -> bool:
        """Check if travel between locations requires transportation."""
        # Simplified logic - in practice, would use distance calculation
        if "home" in loc1.lower() and "home" in loc2.lower():
            return False
        return True
    
    def _insufficient_travel_time(self, event: CalendarEvent, request: ScheduleRequest) -> bool:
        """Check if there's insufficient travel time between events."""
        # Calculate travel time needed
        travel_time = self._calculate_travel_time(event.location, request.location.name)
        
        # Check time between events
        time_between = (request.target_date - event.end_time).total_seconds() / 60
        
        return time_between < travel_time
    
    def _calculate_travel_time(self, loc1: str, loc2: str) -> int:
        """Calculate travel time between locations."""
        # Simplified calculation - would integrate with mapping API
        if "baltimore" in loc1.lower() or "baltimore" in loc2.lower():
            return 90  # 1.5 hours
        elif "lewis center" in loc1.lower() and "lewis center" in loc2.lower():
            return 15  # 15 minutes
        return 30  # Default 30 minutes
    
    def _generate_solutions(self, request: ScheduleRequest) -> List[SchedulingSolution]:
        """Generate solutions for scheduling conflicts."""
        solutions = []
        
        for conflict in self.conflicts:
            if conflict.conflict_type == "overlap":
                solutions.extend(self._suggest_overlap_solutions(conflict, request))
            elif conflict.conflict_type == "transportation":
                solutions.extend(self._suggest_transportation_solutions(conflict, request))
        
        # Add general coordination solutions
        solutions.extend(self._suggest_coordination_solutions(request))
        
        return solutions
    
    def _suggest_overlap_solutions(self, conflict: SchedulingConflict, request: ScheduleRequest) -> List[SchedulingSolution]:
        """Suggest solutions for time overlap conflicts."""
        solutions = []
        
        # Solution 1: Reschedule the request
        solutions.append(SchedulingSolution(
            conflict=conflict,
            solution_type="reschedule",
            description=f"Reschedule {request.title} to avoid conflict with {conflict.event2.title}",
            impact="medium",
            implementation_steps=[
                f"Find alternative time for {request.title}",
                f"Check availability of all required attendees",
                f"Update calendar"
            ],
            required_coordination=conflict.affected_family_members
        ))
        
        # Solution 2: Delegate attendance
        solutions.append(SchedulingSolution(
            conflict=conflict,
            solution_type="delegate",
            description=f"Have someone else handle {request.title}",
            impact="low",
            implementation_steps=[
                f"Identify available family member",
                f"Coordinate handoff",
                f"Provide necessary information"
            ],
            required_coordination=conflict.affected_family_members
        ))
        
        return solutions
    
    def _suggest_transportation_solutions(self, conflict: SchedulingConflict, request: ScheduleRequest) -> List[SchedulingSolution]:
        """Suggest solutions for transportation conflicts."""
        solutions = []
        
        # Solution 1: Coordinate transportation
        solutions.append(SchedulingSolution(
            conflict=conflict,
            solution_type="coordinate",
            description=f"Coordinate transportation between {conflict.event2.title} and {request.title}",
            impact="medium",
            implementation_steps=[
                f"Arrange ride sharing between events",
                f"Coordinate with other family members",
                f"Plan route and timing"
            ],
            required_coordination=conflict.affected_family_members
        ))
        
        # Solution 2: Use alternative transportation
        solutions.append(SchedulingSolution(
            conflict=conflict,
            solution_type="modify",
            description=f"Use alternative transportation for {request.title}",
            impact="low",
            implementation_steps=[
                f"Arrange ride sharing service",
                f"Coordinate with family members",
                f"Update travel plans"
            ],
            required_coordination=conflict.affected_family_members
        ))
        
        return solutions
    
    def _suggest_coordination_solutions(self, request: ScheduleRequest) -> List[SchedulingSolution]:
        """Suggest general coordination solutions."""
        solutions = []
        
        # Solution: Family coordination meeting
        if len(request.required_attendees) > 1:
            solutions.append(SchedulingSolution(
                conflict=None,
                solution_type="coordinate",
                description=f"Coordinate {request.title} with all family members",
                impact="low",
                implementation_steps=[
                    f"Schedule family coordination meeting",
                    f"Discuss logistics and timing",
                    f"Assign responsibilities",
                    f"Update everyone's calendars"
                ],
                required_coordination=request.required_attendees
            ))
        
        return solutions
    
    def create_calendar_event(self, request: ScheduleRequest, calendar_name: str = "Family") -> bool:
        """Create a calendar event for the scheduling request."""
        try:
            # Use the simpler date format that AppleScript can reliably parse
            start_time = request.target_date.strftime('%m/%d/%Y %I:%M:%S %p')
            end_time = (request.target_date + timedelta(minutes=request.duration_minutes)).strftime('%m/%d/%Y %I:%M:%S %p')
            
            script = f'tell application "Calendar" to make new event at end of events of calendar "{calendar_name}" with properties {{summary:"{request.title}", start date:date "{start_time}", end date:date "{end_time}", location:"{request.location.address}", description:"{request.description}"}}'
            
            import subprocess
            result = subprocess.run(['osascript', '-e', script], 
                                  capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"✅ Created calendar event: {request.title}")
                return True
            else:
                print(f"❌ Error creating calendar event: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"❌ Error creating calendar event: {e}")
            return False

def create_scheduling_request(title: str, description: str, date_str: str, 
                            location_name: str, attendees: List[str], 
                            duration_minutes: int = 60, time_str: str = "08:00") -> ScheduleRequest:
    """Helper function to create a scheduling request."""
    
    # Parse date and time
    if " " in date_str:
        # Date string includes time
        target_date = datetime.strptime(date_str, "%Y-%m-%d %H:%M")
    else:
        # Date string only, add default time
        date_only = datetime.strptime(date_str, "%Y-%m-%d")
        hour, minute = map(int, time_str.split(":"))
        target_date = date_only.replace(hour=hour, minute=minute)
    
    # Get location
    scheduler = FamilyScheduler()
    location = scheduler.known_locations.get(location_name.lower().replace(" ", "_"), 
                                           Location(name=location_name, address=location_name))
    
    # Convert attendee strings to FamilyMember enums
    family_attendees = []
    for attendee in attendees:
        try:
            family_attendees.append(FamilyMember(attendee))
        except ValueError:
            print(f"Warning: Unknown family member '{attendee}'")
    
    return ScheduleRequest(
        title=title,
        description=description,
        target_date=target_date,
        location=location,
        required_attendees=family_attendees,
        duration_minutes=duration_minutes
    )

def analyze_family_scheduling(title: str, description: str, date_str: str,
                            location_name: str, attendees: List[str],
                            duration_minutes: int = 60) -> Dict:
    """Main function to analyze family scheduling scenarios."""
    
    # Create scheduling request
    request = create_scheduling_request(title, description, date_str, 
                                      location_name, attendees, duration_minutes)
    
    # Create scheduler and analyze
    scheduler = FamilyScheduler()
    analysis = scheduler.analyze_scheduling_request(request)
    
    return analysis

if __name__ == "__main__":
    # Example usage
    analysis = analyze_family_scheduling(
        title="Evan Car Repair",
        description="Drop off Evan's car at Crash Champions for repair",
        date_str="2025-07-19",
        location_name="crash_champions",
        attendees=["Evan"],
        duration_minutes=30
    )
    
    print(json.dumps(analysis, indent=2, default=str)) 