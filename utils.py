"""
Utility functions for the OFCLI tool.
"""

import os
import sys
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

def load_env_vars() -> None:
    """
    Load environment variables from .env files in the following order:
    1. .ofcli.env in the current directory
    2. .ofcli.env in the user's home directory
    """
    # Load from current directory
    if os.path.exists(".ofcli.env"):
        load_dotenv(".ofcli.env")
    
    # Load from home directory
    home_env = Path.home() / ".ofcli.env"
    if home_env.exists():
        load_dotenv(home_env)

def get_api_key(service: str) -> Optional[str]:
    """
    Get API key for a specific service.
    
    Args:
        service: The service to get the API key for ("openai" or "anthropic")
        
    Returns:
        The API key if available, None otherwise
    """
    env_var = f"{service.upper()}_API_KEY"
    api_key = os.environ.get(env_var)
    
    if not api_key:
        print(f"Warning: {env_var} not found in environment variables.")
        print(f"AI features using {service.title()} will not work.")
        print(f"Set your {service.title()} API key in $HOME/.ofcli.env")
        return None
    
    return api_key 