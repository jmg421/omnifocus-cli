import os
import traceback
from openai import OpenAI
from ai_integration.utils.config import get_config

def openai_completion(prompt: str) -> str:
    """
    Calls OpenAI's ChatCompletion API (GPT-3.5 or GPT-4) with the given prompt.
    Returns the model's response text.
    """
    cfg = get_config()
    api_key = os.environ.get("OPENAI_API_KEY", cfg.get("OPENAI_API_KEY", ""))
    
    if not api_key:
        raise ValueError("OpenAI API key is not set. Please set OPENAI_API_KEY environment variable.")
    
    try:
        print("Creating OpenAI client...")
        # Create a new client instance with only the required parameters
        client = OpenAI(api_key=api_key)
        
        print("Calling completions API...")
        # Call the completion API
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",  # or "gpt-4" for more advanced reasoning
            messages=[
                {"role": "system", "content": "You are a helpful assistant for OmniFocus task management."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1000
        )
        
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error calling OpenAI API: {e}")
        print("Traceback:")
        traceback.print_exc()
        return f"Error: {str(e)}"

