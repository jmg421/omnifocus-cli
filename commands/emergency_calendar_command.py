#!/usr/bin/env python3
"""
Emergency Calendar Command for OmniFocus CLI

This command provides fallback calendar access when automated methods fail.
Integrated into the ofcli.py system for immediate use.
"""

import sys
import os
import subprocess
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional

# Add the parent directory to the path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

def handle_emergency_calendar(args):
    """Handle emergency calendar access when automated methods fail."""
    print("🚨 Emergency Calendar Access")
    print("=" * 50)
    print("Note: This is used when normal AppleScript calendar integration times out")
    print()
    
    # Quick system check
    print("📊 System Status Check:")
    
    # Check current date
    try:
        script = 'set currentDate to current date\nreturn currentDate as string'
        result = subprocess.run(['osascript', '-e', script], 
                              capture_output=True, text=True, timeout=2)
        current_date = result.stdout.strip() if result.returncode == 0 else "Unknown"
        print(f"  📅 Current date: {current_date}")
    except:
        print(f"  ❌ Date check failed")
    
    # Check calendar access
    try:
        script = 'tell application "Calendar"\nreturn count of calendars\nend tell'
        result = subprocess.run(['osascript', '-e', script], 
                              capture_output=True, text=True, timeout=2)
        calendar_count = result.stdout.strip() if result.returncode == 0 else "Unknown"
        print(f"  📊 Available calendars: {calendar_count}")
    except:
        print(f"  ❌ Calendar access failed")
    
    print()
    
    # Open Calendar.app for manual verification
    print("🔍 Opening Calendar.app for manual verification...")
    
    try:
        # Create and run script to open Calendar.app
        calendar_script = '''
        tell application "Calendar"
            activate
        end tell
        
        delay 1
        tell application "Calendar"
            activate
        end tell
        '''
        
        result = subprocess.run(['osascript', '-e', calendar_script], 
                              capture_output=True, text=True, timeout=5)
        
        if result.returncode == 0:
            print("✅ Calendar.app opened successfully")
        else:
            print(f"❌ Error opening Calendar.app: {result.stderr}")
    except Exception as e:
        print(f"❌ Error opening Calendar.app: {e}")
    
    print()
    
    # Provide manual verification instructions
    today = datetime.now()
    tomorrow = today + timedelta(days=1)
    
    print("📋 Manual Verification Instructions:")
    print(f"1. In Calendar.app, check today ({today.strftime('%B %d, %Y')})")
    print(f"2. Check tomorrow ({tomorrow.strftime('%B %d, %Y')})")
    print("3. Focus on these calendars (known to have many events):")
    print("   • Family")
    print("   • John")
    print("   • Christina")
    print("   • Grace")
    print("   • Evan")
    print("   • Weston")
    print("4. Look for any events in the next 24 hours")
    print("5. Note any upcoming events you find")
    
    print()
    print("💡 Why manual verification is needed:")
    print("   • All calendars (even small ones) time out in AppleScript")
    print("   • This indicates a system-level issue with automated calendar access")
    print("   • Manual verification is the most reliable method")
    print("   • icalBuddy also failed due to permission issues")
    
    print()
    print("🎯 After manual verification:")
    print("   • Use 'ofcli.py add-task' to add any urgent items found")
    print("   • Focus on horizon-0 and horizon-1 items for OmniFocus")
    print("   • Consider updating this system based on your findings")

def handle_emergency_calendar_report(args):
    """Generate a detailed emergency calendar report."""
    print("📊 Emergency Calendar Analysis Report")
    print("=" * 60)
    
    report = {
        "timestamp": datetime.now().isoformat(),
        "analysis_type": "emergency_fallback",
        "automated_methods_status": "FAILED",
        "reasons": []
    }
    
    # Test different calendar access methods
    print("🔍 Testing Calendar Access Methods:")
    
    # Test 1: Basic AppleScript calendar count
    print("\n1️⃣  Basic calendar count...")
    try:
        script = 'tell application "Calendar"\nreturn count of calendars\nend tell'
        result = subprocess.run(['osascript', '-e', script], 
                              capture_output=True, text=True, timeout=3)
        if result.returncode == 0:
            count = result.stdout.strip()
            print(f"   ✅ Found {count} calendars")
            report["calendar_count"] = count
        else:
            print(f"   ❌ Failed: {result.stderr}")
            report["reasons"].append("basic_calendar_count_failed")
    except subprocess.TimeoutExpired:
        print("   ⏰ Timeout (3s)")
        report["reasons"].append("basic_calendar_count_timeout")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        report["reasons"].append(f"basic_calendar_count_error: {e}")
    
    # Test 2: Single event query from smallest calendar
    print("\n2️⃣  Single event from Force Aquatics calendar...")
    try:
        script = '''
        tell application "Calendar"
            set cal to calendar "Force Aquatics"
            set eventCount to count of events of cal
            return eventCount
        end tell
        '''
        result = subprocess.run(['osascript', '-e', script], 
                              capture_output=True, text=True, timeout=3)
        if result.returncode == 0:
            count = result.stdout.strip()
            print(f"   ✅ Force Aquatics has {count} events")
            report["force_aquatics_events"] = count
        else:
            print(f"   ❌ Failed: {result.stderr}")
            report["reasons"].append("force_aquatics_query_failed")
    except subprocess.TimeoutExpired:
        print("   ⏰ Timeout (3s)")
        report["reasons"].append("force_aquatics_query_timeout")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        report["reasons"].append(f"force_aquatics_query_error: {e}")
    
    # Test 3: Date comparison test
    print("\n3️⃣  Date handling test...")
    try:
        script = '''
        set today to current date
        set tomorrow to today + (24 * 60 * 60)
        return (today as string) & " | " & (tomorrow as string)
        '''
        result = subprocess.run(['osascript', '-e', script], 
                              capture_output=True, text=True, timeout=2)
        if result.returncode == 0:
            dates = result.stdout.strip()
            print(f"   ✅ Date handling works: {dates}")
            report["date_handling"] = dates
        else:
            print(f"   ❌ Failed: {result.stderr}")
            report["reasons"].append("date_handling_failed")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        report["reasons"].append(f"date_handling_error: {e}")
    
    # Analysis
    print(f"\n📊 Analysis:")
    if len(report["reasons"]) == 0:
        print("   🤔 Calendar access works but event queries are slow")
        print("   💡 Likely cause: Large number of events causing timeouts")
        report["probable_cause"] = "large_event_volume_causing_timeouts"
        report["recommendation"] = "use_manual_verification"
    else:
        print(f"   ❌ Multiple failures detected: {len(report['reasons'])}")
        print("   💡 Likely cause: System-level calendar access issue")
        report["probable_cause"] = "system_level_calendar_access_issue"
        report["recommendation"] = "manual_verification_only"
    
    # Save report
    output_file = "emergency_calendar_analysis.json"
    with open(output_file, 'w') as f:
        json.dump(report, f, indent=2, default=str)
    
    print(f"\n💾 Report saved to: {output_file}")
    
    return report

# Integration functions for the main CLI
def emergency_calendar_test():
    """Quick test function for CLI integration."""
    args = type('Args', (), {})
    handle_emergency_calendar(args)

def emergency_calendar_analysis():
    """Analysis function for CLI integration."""
    args = type('Args', (), {})
    return handle_emergency_calendar_report(args) 