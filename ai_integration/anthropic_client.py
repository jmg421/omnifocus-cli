import os
import requests
from omnifocus_cli.utils.config import get_config

def anthropic_completion(prompt: str) -> str:
    """
    Calls Anthropic's Claude API with the given prompt.
    Returns the model's response text.
    """
    cfg = get_config()
    api_key = cfg.get("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("Anthropic API key is not set.")

    url = "https://api.anthropic.com/v1/complete"

    headers = {
        "x-api-key": api_key,
        "Content-Type": "application/json"
    }

    json_data = {
        "prompt": f"\n\nHuman: {prompt}\n\nAssistant:",
        "model": "claude-v1",
        "max_tokens_to_sample": 500,
        "temperature": 0.7
    }

    try:
        resp = requests.post(url, headers=headers, json=json_data, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        return data.get("completion", "").strip()
    except Exception as e:
        return f"Error from Anthropic: {str(e)}"

