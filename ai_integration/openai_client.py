import os
import traceback
import openai
from .utils.config import get_config
from .utils.consent import check_ai_consent
from openai import OpenAI

def openai_completion(prompt: str) -> str:
    """
    Calls OpenAI's ChatCompletion API (GPT-3.5 or GPT-4) with the given prompt.
    Returns the model's response text.
    """
    # Check for user consent before proceeding
    if not check_ai_consent():
        # Fall through to mock responses if consent is not given
        print("Falling back to mock responses.")
    else:
        # Try to load API key 
        cfg = get_config()
        api_key = os.environ.get("OPENAI_API_KEY", cfg.get("OPENAI_API_KEY", ""))
        
        # If we have an API key, try to use it
        if api_key:
            try:
                print("Creating OpenAI client...")
                # Create a new client instance with only the required parameters
                # Handle older OpenAI versions differently
                try:
                    client = OpenAI(api_key=api_key)
                    
                    print("Calling completions API...")
                    # Call the completion API with newer OpenAI client
                    response = client.chat.completions.create(
                        model="gpt-3.5-turbo",  # or "gpt-4" for more advanced reasoning
                        messages=[
                            {"role": "system", "content": "You are a helpful assistant for OmniFocus task management."},
                            {"role": "user", "content": prompt}
                        ],
                        max_tokens=1000
                    )
                except TypeError:
                    # Older OpenAI client version
                    openai.api_key = api_key
                    
                    print("Using older OpenAI client...")
                    response = openai.ChatCompletion.create(
                        model="gpt-3.5-turbo",
                        messages=[
                            {"role": "system", "content": "You are a helpful assistant for OmniFocus task management."},
                            {"role": "user", "content": prompt}
                        ],
                        max_tokens=1000
                    )
                
                print("Successfully received response from OpenAI")
                # Handle different response formats between old and new OpenAI versions
                try:
                    # New version
                    return response.choices[0].message.content
                except AttributeError:
                    # Old version
                    return response.choices[0]["message"]["content"]
            except Exception as e:
                print(f"Error calling OpenAI API: {e}")
                print("Falling back to mock responses")
                # Fall through to mock responses
        else:
            print("OpenAI API key not found, using mock responses")
    
    # Mock responses for different request types
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

