# Sample Prompt Templates

Sometimes it's helpful to store longer prompts or partial prompts in files
and load them at runtime. This file demonstrates how you might keep
prompt text separate for easier editing.

## Task Prioritization Template

```json
{
  "name": "task_prioritization",
  "prompt": "# Task Prioritization Request\n\nI need help prioritizing the following tasks from my OmniFocus task manager:\n\n## Tasks\n{task_details}\n\n## Contexts\n{context_info}\n\n{duplicate_info}\n\nPlease analyze these tasks and help me prioritize them by:\n1. Grouping them into 2-3 priority levels (High, Medium, Low)\n2. Suggesting which 2-3 tasks I should focus on first\n3. Identifying any tasks that could be delegated or deferred\n4. Noting potential duplicates that should be merged\n5. Suggesting any tasks that could be broken down further\n\nFor my Finance project specifically, please help me simplify and structure these tasks in a more manageable way.\n\nPlease format your response as Markdown with clear headings and bullet points."
}
```

## Finance Project Organization Template

```json
{
  "name": "finance_project_organization",
  "prompt": "# Finance Project Organization Request\n\nI need help organizing and simplifying my finance-related tasks in OmniFocus. Here are my current finance tasks:\n\n{finance_tasks}\n\nPlease help me:\n\n1. Identify duplicate or redundant tasks that can be consolidated\n2. Group related tasks into logical categories (e.g., budgeting, investments, tax planning)\n3. Suggest a hierarchical structure (projects and sub-tasks) for better organization\n4. Identify any tasks that could be broken down into smaller, more actionable steps\n5. Suggest a timeline or sequence for tackling these finance tasks\n\nPlease structure your response with clear headings and bullet points."
}
```

## Task Deduplication Template

```json
{
  "name": "task_deduplication",
  "prompt": "# Task Deduplication Request\n\nI need help identifying and consolidating duplicate tasks in my OmniFocus system. Here are tasks that might be duplicates:\n\n{potential_duplicates}\n\nFor each pair of potential duplicates, please:\n\n1. Analyze whether they are truly duplicates or just similar but distinct tasks\n2. If they are duplicates, suggest which one to keep and which to delete\n3. If they are distinct but related, suggest how to clarify their names and relationship\n\nPlease format your response as a markdown list with clear recommendations for each pair."
}
```

You can load these templates and insert dynamic content in your Python code using the `get_prompt_template` function in `prompt_utils.py`.

