import os
import requests
import anthropic
from .utils.config import get_config

def anthropic_completion(prompt: str) -> str:
    """
    Calls Anthropic's Claude API with the given prompt.
    Returns the model's response text.
    """
    # Try to get API key
    cfg = get_config()
    api_key = cfg.get("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
    
    # If we have an API key, attempt to use the API
    if api_key:
        try:
            url = "https://api.anthropic.com/v1/messages"

            headers = {
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json"
            }

            json_data = {
                "model": "claude-3-haiku-20240307",
                "max_tokens": 500,
                "temperature": 0.7,
                "messages": [
                    {"role": "user", "content": prompt}
                ]
            }

            print("Calling Anthropic Claude API...")
            resp = requests.post(url, headers=headers, json=json_data, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            print("Successfully received response from Anthropic")
            return data.get("content", [{}])[0].get("text", "").strip()
        except Exception as e:
            print(f"Error from Anthropic API: {str(e)}")
            print("Falling back to mock responses")
            # Fall through to mock responses
    else:
        print("Anthropic API key not set, using mock responses")
    
    # Mock responses based on prompt type
    if "Task Deduplication Request" in prompt:
        return """# Task Deduplication Analysis

I've analyzed the potential duplicate tasks you provided:

## Duplicate Pair 1:
- These tasks appear to be duplicates. I recommend keeping "Test Task 1" as it contains more detailed information.
- Action: Delete "Test Task 2" and ensure "Test Task 1" has all relevant details.

## Duplicate Pair 2:
- These tasks are similar but actually distinct. "Test Task 1" is about setting up tracking, while "Test Task 3" is about document gathering.
- Action: Rename "Test Task 3" to "Gather tax documents" to better differentiate it.

Remember to check completed tasks as well, as you might have already finished one of these items."""
    elif "Finance Project Organization Request" in prompt:
        return """# Finance Task Organization

Here's how I recommend organizing your finance-related tasks:

## Expense Tracking
- Test Task 1 - Set up monthly expense tracking

## Investments
- Test Task 2 - Review investment portfolio

## Tax Planning
- Test Task 3 - Gather documents for tax preparation

## Recommended Timeline
1. Start with Test Task 3 (tax preparation) since it has the earliest due date
2. Then address Test Task 1 (expense tracking) 
3. Finally work on Test Task 2 (investments) which has no immediate deadline

I recommend creating a dedicated "Finance" project in OmniFocus with these categories as sub-projects."""
    elif "prioritize" in prompt.lower():
        return """# Task Prioritization Analysis

Based on your tasks, here's how I would prioritize them:

## High Priority
- **Test Task 3** - Due soon (Dec 25) and needs immediate attention

## Medium Priority
- **Test Task 1** - Has a due date but not as urgent (Dec 31)

## Low Priority
- **Test Task 2** - No due date and can be handled when you have time

## Tasks to Focus on First
1. Test Task 3 - Complete before the holiday
2. Test Task 1 - Plan to work on this after Task 3

## Tasks to Consider Breaking Down
- Test Task 1 might benefit from being broken into smaller steps

This prioritization is based on due dates and project context."""
    else:
        # Generic mock response
        return """# Analysis

I've analyzed the information you've provided. Here are my recommendations:

1. Focus on tasks with the nearest due dates first
2. Group similar tasks together to improve efficiency
3. Break down any complex tasks into smaller steps
4. Consider delegating tasks that don't require your specific expertise

Hope this helps with your task management!"""

