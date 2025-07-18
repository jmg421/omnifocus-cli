#!/usr/bin/env python3
"""
Batch Inbox Organization Script
Systematically moves inbox items to appropriate projects using MCP tools
"""

import json
import sys
from omnifocus_api.apple_script_client import execute_omnifocus_applescript  # Unified helper
import time
from typing import List, Dict, Tuple

def load_inbox_tasks() -> List[Dict]:
    """Load inbox tasks from JSON export"""
    try:
        with open('../data/omnifocus_export.json', 'r') as f:
            data = json.load(f)
        return data.get('inboxTasks', [])
    except Exception as e:
        print(f"Error loading JSON: {e}")
        return []

def categorize_task(task: Dict) -> str:
    """Categorize task based on content"""
    name = task.get('name', '').lower()
    note = task.get('note', '').lower()
    content = f"{name} {note}"
    
    # Reference materials
    if any(word in content for word in ['amazon', 'book', 'website', 'stewardship', 'mythos', 'kindle', 'read']):
        return 'Reference Materials'
    
    # Estate Planning & Legal
    elif any(word in content for word in ['trust', 'attorney', 'poa', 'wealth', 'trustee', 'estate', 'legal', 'will', 'beneficiary']):
        return 'Estate Planning & Legal'
    
    # Family Coordination
    elif any(word in content for word in ['christina', 'family', 'weston', 'state of the union', 'meeting', 'parade', 'evan car repair']):
        return 'Family Coordination'
    
    # Keep in inbox for manual review
    else:
        return 'MANUAL_REVIEW'

def move_task_to_project(task_id: str, project_name: str, task_name: str) -> bool:
    """Move task to project using direct AppleScript"""
    try:
        # Create AppleScript to move the task
        applescript = f'''
tell application "OmniFocus"
    tell default document
        set theTask to first flattened task whose id is "{task_id}"
        set theProject to first flattened project whose name is "{project_name}"
        move theTask to theProject
    end tell
end tell
'''
        
        # Execute via unified helper
        execute_omnifocus_applescript(applescript)
        print(f"  ✅ Moved: {task_name[:60]}...")
        return True
            
    except Exception as e:
        print(f"  ❌ Error moving task: {e}")
        return False

def main():
    """Main execution function"""
    print("🎯 BATCH INBOX ORGANIZATION")
    print("=" * 50)
    
    # Load inbox tasks
    inbox_tasks = load_inbox_tasks()
    if not inbox_tasks:
        print("No inbox tasks found!")
        return
    
    print(f"Found {len(inbox_tasks)} inbox tasks to process\\n")
    
    # Categorize and group tasks
    categories = {
        'Reference Materials': [],
        'Estate Planning & Legal': [],
        'Family Coordination': [],
        'MANUAL_REVIEW': []
    }
    
    for task in inbox_tasks:
        category = categorize_task(task)
        categories[category].append(task)
    
    # Show categorization summary
    print("📊 CATEGORIZATION SUMMARY:")
    for category, tasks in categories.items():
        if category != 'MANUAL_REVIEW':
            print(f"  📁 {category}: {len(tasks)} tasks")
    print(f"  ⚠️  Manual Review: {len(categories['MANUAL_REVIEW'])} tasks")
    print()
    
    # Process each category
    total_moved = 0
    
    for project_name, tasks in categories.items():
        if project_name == 'MANUAL_REVIEW' or not tasks:
            continue
            
        print(f"📁 Moving {len(tasks)} tasks to '{project_name}':")
        moved_count = 0
        
        for task in tasks:
            task_id = task.get('id')
            task_name = task.get('name', 'Unnamed task')
            
            if move_task_to_project(task_id, project_name, task_name):
                moved_count += 1
                total_moved += 1
            
            # Small delay to prevent overwhelming the system
            time.sleep(0.2)
        
        print(f"  📊 Moved {moved_count}/{len(tasks)} tasks to {project_name}\\n")
    
    # Summary
    remaining_inbox = len(inbox_tasks) - total_moved
    reduction_pct = (total_moved / len(inbox_tasks)) * 100
    
    print("🎉 ORGANIZATION COMPLETE!")
    print(f"📊 Results:")
    print(f"  ✅ Tasks moved: {total_moved}")
    print(f"  📥 Remaining in inbox: {remaining_inbox}")
    print(f"  📈 Reduction: {reduction_pct:.1f}%")
    
    if categories['MANUAL_REVIEW']:
        print(f"\\n⚠️  Items requiring manual review:")
        for task in categories['MANUAL_REVIEW'][:5]:  # Show first 5
            print(f"    • {task.get('name', 'Unnamed')[:60]}...")
        if len(categories['MANUAL_REVIEW']) > 5:
            print(f"    ... and {len(categories['MANUAL_REVIEW']) - 5} more")

if __name__ == "__main__":
    main() 