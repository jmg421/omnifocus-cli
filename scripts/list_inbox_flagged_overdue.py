import json
from datetime import datetime

with open('omni-cli/temp_all_tasks.json') as f:
    tasks = json.load(f)

def sortkey(t):
    # Use createdDate, then addedDate, then dueDate, then name
    return t.get('createdDate') or t.get('addedDate') or t.get('dueDate') or t.get('name') or ''

def print_tasks(title, tasks):
    print(f'\n{title} (most recent first):')
    for t in sorted(tasks, key=sortkey, reverse=True):
        print(f"- {t.get('name')} [Due: {t.get('dueDate')}] [Flagged: {t.get('flagged')}] [Created: {t.get('createdDate')}] [Completed: {t.get('completed')}] [ID: {t.get('id')}]" )

# Only include incomplete tasks
incomplete = [t for t in tasks if not t.get('completed')]
# Inbox: no projectId
inbox = [t for t in incomplete if not t.get('projectId')]
# Flagged: flagged == True
flagged = [t for t in incomplete if t.get('flagged')]
# Overdue: dueDate < today and not completed
now = datetime.now().date()
overdue = [t for t in incomplete if t.get('dueDate') and datetime.fromisoformat(t['dueDate'].replace('Z','+00:00')).date() < now]

print_tasks('INBOX', inbox)
print_tasks('FLAGGED', flagged)
print_tasks('OVERDUE', overdue) 