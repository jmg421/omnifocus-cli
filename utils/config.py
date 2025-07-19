"""
Configuration utilities for the OFCLI tool.
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

def get_config(key: str, default: Optional[str] = None) -> Optional[str]:
    """Get configuration value from environment variables."""
    return os.getenv(key, default)

def ensure_api_keys() -> bool:
    """Ensure required API keys are available."""
    required_keys = ["OPENAI_API_KEY", "ANTHROPIC_API_KEY"]
    missing_keys = [key for key in required_keys if not os.getenv(key)]
    
    if missing_keys:
        print(f"Missing required API keys: {', '.join(missing_keys)}")
        print("Please set them in your .ofcli.env file or environment variables.")
        return False
    
    return True 