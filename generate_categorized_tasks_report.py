import json
import os
from datetime import datetime, date
from collections import Counter, defaultdict
import matplotlib.pyplot as plt
import glob

CATEGORIZED_TASKS_PATH = "data/categorized_tasks.json"
REPORT_PATH = "data/categorized_tasks_report.md"
CHART_PATH = "data/categorized_tasks_chart.png"

def parse_due_date(due):
    if not due:
        return None
    try:
        return datetime.fromisoformat(due.replace('Z', '+00:00')).date()
    except Exception:
        return None

def get_latest_export_path():
    files = glob.glob("data/omnifocus-export-*.json")
    if not files:
        return None
    files.sort(reverse=True)
    return files[0]

def main():
    # Load categorized tasks
    if not os.path.exists(CATEGORIZED_TASKS_PATH):
        print(f"File not found: {CATEGORIZED_TASKS_PATH}")
        return
    with open(CATEGORIZED_TASKS_PATH, 'r', encoding='utf-8') as f:
        tasks = json.load(f)
    # Find and load latest export for inbox tasks
    export_path = get_latest_export_path()
    if export_path:
        print(f"Using latest OmniFocus export: {export_path}")
    else:
        print("No OmniFocus export file found matching 'data/omnifocus-export-*.json'.")
    inbox_tasks = []
    if export_path and os.path.exists(export_path):
        with open(export_path, 'r', encoding='utf-8') as f:
            export = json.load(f)
            inbox_tasks = export.get('inboxTasks', [])
            for t in inbox_tasks:
                t['inbox'] = True
    # Merge inbox tasks (avoid duplicates by id)
    all_ids = {t['id'] for t in tasks}
    merged_tasks = tasks + [t for t in inbox_tasks if t['id'] not in all_ids]
    total = len(merged_tasks)
    actionable = [t for t in merged_tasks if t.get('management_category') == 'Actionable' or t.get('inbox')]
    reference = [t for t in merged_tasks if t.get('management_category', '').startswith('Reference') and not t.get('inbox')]
    flagged = [t for t in actionable if t.get('flagged')]
    inbox = [t for t in merged_tasks if t.get('inbox')]
    flagged_inbox = [t for t in inbox if t.get('flagged')]
    # Overdue: actionable, dueDate in past
    today = date.today()
    overdue = [t for t in actionable if t.get('dueDate') and parse_due_date(t.get('dueDate')) and parse_due_date(t.get('dueDate')) < today]
    # By project (if available)
    by_project = defaultdict(list)
    for t in actionable:
        proj = t.get('projectId') or t.get('project') or ('Inbox' if t.get('inbox') else 'Unknown')
        by_project[proj].append(t)
    # Subtasks
    subtasks = [t for t in merged_tasks if t.get('parentId')]
    # Markdown report
    with open(REPORT_PATH, 'w', encoding='utf-8') as f:
        f.write(f"# Categorized OmniFocus Tasks Report\n\n")
        f.write(f"**Generated:** {datetime.now().isoformat()}\n\n")
        f.write(f"- **Total tasks:** {total}\n")
        f.write(f"- **Actionable:** {len(actionable)}\n")
        f.write(f"- **Reference:** {len(reference)}\n")
        f.write(f"- **Inbox items:** {len(inbox)}\n")
        f.write(f"- **Flagged actionable:** {len(flagged)}\n")
        f.write(f"- **Flagged inbox:** {len(flagged_inbox)}\n")
        f.write(f"- **Overdue actionable:** {len(overdue)}\n")
        f.write(f"- **Subtasks:** {len(subtasks)}\n\n")
        f.write(f"## Actionable Tasks by Project\n\n")
        for proj, tasks_in_proj in by_project.items():
            f.write(f"- **{proj}**: {len(tasks_in_proj)}\n")
        f.write(f"\n## Sample Inbox Tasks\n\n")
        for t in inbox[:10]:
            f.write(f"- {t.get('name')} (Flagged: {t.get('flagged')}, Due: {t.get('dueDate')})\n")
        f.write(f"\n## Sample Overdue Actionable Tasks\n\n")
        for t in overdue[:10]:
            f.write(f"- {t.get('name')} (Due: {t.get('dueDate')}, Project: {t.get('projectId')})\n")
    # Bar chart
    labels = ['Actionable', 'Reference', 'Inbox', 'Flagged', 'Flagged Inbox', 'Overdue', 'Subtasks']
    values = [len(actionable), len(reference), len(inbox), len(flagged), len(flagged_inbox), len(overdue), len(subtasks)]
    plt.figure(figsize=(10,5))
    plt.bar(labels, values, color=['#4caf50', '#607d8b', '#2196f3', '#ff9800', '#00bcd4', '#f44336', '#9c27b0'])
    plt.title('OmniFocus Task Categories (Enhanced)')
    plt.ylabel('Count')
    for i, v in enumerate(values):
        plt.text(i, v + 2, str(v), ha='center', va='bottom')
    plt.tight_layout()
    plt.savefig(CHART_PATH)
    print(f"Report saved to {REPORT_PATH}")
    print(f"Chart saved to {CHART_PATH}")

if __name__ == "__main__":
    main() 