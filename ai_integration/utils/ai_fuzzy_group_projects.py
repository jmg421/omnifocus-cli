import json
from thefuzz import fuzz
from collections import Counter
import re

SIMILARITY_THRESHOLD = 80

with open('active_project_names.json', 'r') as f:
    projects = json.load(f)

# Prepare a list of (id, name)
project_names = [(p['id'], p['name']) for p in projects]

# Grouping logic
visited = set()
groups = []

def suggest_group_name(names):
    # Tokenize and count most common word (ignoring very short words)
    words = []
    for n in names:
        words += [w.lower() for w in re.findall(r"\w+", n) if len(w) > 2]
    if not words:
        return "Group"
    most_common, _ = Counter(words).most_common(1)[0]
    return most_common.capitalize() + " Group"

for i, (id1, name1) in enumerate(project_names):
    if id1 in visited:
        continue
    group = [(id1, name1)]
    visited.add(id1)
    for j, (id2, name2) in enumerate(project_names):
        if i == j or id2 in visited:
            continue
        score = fuzz.token_set_ratio(name1, name2)
        if score >= SIMILARITY_THRESHOLD:
            group.append((id2, name2))
            visited.add(id2)
    if len(group) > 1:
        groups.append(group)

# Print groups with suggested names
print("Fuzzy Groups of Similar Projects (threshold {}):\n".format(SIMILARITY_THRESHOLD))
for idx, group in enumerate(groups, 1):
    group_names = [name for (_, name) in group]
    group_label = suggest_group_name(group_names)
    print(f"Group {idx} ({group_label}):")
    for pid, pname in group:
        print(f"  - {pname} (ID: {pid})")
    print()

# Print projects not in any group
ungrouped = [name for (id, name) in project_names if id not in visited]
if ungrouped:
    print("Projects not grouped:")
    for pname in ungrouped:
        print(f"  - {pname}") 