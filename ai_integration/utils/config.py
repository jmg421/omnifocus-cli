import os
import json
from pathlib import Path

_config_cache = None

def get_config():
    """
    Loads config settings from a local JSON file, .env, or environment variables.
    Caches them in _config_cache for quick subsequent access.
    """
    global _config_cache
    if _config_cache is not None:
        return _config_cache

    config_dict = {}

    # Example: load a config.json if you want
    config_path = Path(__file__).parent.parent.parent / "config.json"
    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as cf:
                file_conf = json.load(cf)
                config_dict.update(file_conf)
        except Exception:
            pass

    # Merge environment variables if needed
    # For example, if OPENAI_API_KEY is in environment, use that
    env_openai_key = os.getenv("OPENAI_API_KEY")
    if env_openai_key:
        config_dict["OPENAI_API_KEY"] = env_openai_key

    env_anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    if env_anthropic_key:
        config_dict["ANTHROPIC_API_KEY"] = env_anthropic_key

    _config_cache = config_dict
    return _config_cache

