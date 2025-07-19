"""ensure_export.py
Utility for omni-cli: guarantee a recent OmniFocus JSON export is available.

• Looks for files matching ~/Desktop/omnifocus-export-*.json (created by the AppleScript).
• If none exist or the newest is older than `max_age_seconds`, it runs the AppleScript exporter
  (which copies the path to stdout) and returns that path.
• Includes file-based caching to prevent multiple exports across command invocations.

Usage:
    from utils.ensure_export import ensure_fresh_export
    path = ensure_fresh_export(max_age_seconds=1800)
"""
from __future__ import annotations

import os
import glob
import subprocess
import pathlib
import time
import json
from typing import Optional

# Cache file path
CACHE_FILE = os.path.join(os.path.dirname(__file__), "export_cache.json")

# Relative path from repo root to AppleScript
APPLE_SCRIPT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "OmniFocus-MCP",
    "scripts",
    "auto_export_master_plan.applescript",
)

# Glob patterns for exported JSON files (prioritize data/exports over Desktop)
EXPORT_GLOB_DATA = "data/exports/*/*/omnifocus-export-*.json"
EXPORT_GLOB_DESKTOP = os.path.expanduser("~/Desktop/omnifocus-export-*.json")


def _load_cache() -> dict:
    """Load cache from file."""
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {"path": None, "timestamp": 0, "max_age": 0}


def _save_cache(cache_data: dict):
    """Save cache to file."""
    try:
        with open(CACHE_FILE, 'w') as f:
            json.dump(cache_data, f)
    except IOError:
        pass  # Silently fail if we can't write cache


def _newest_export_path() -> Optional[str]:
    """Return newest export file path or None if none exist."""
    # First try data/exports directory
    files = glob.glob(EXPORT_GLOB_DATA)
    if files:
        # Sort by modification time descending
        newest = max(files, key=os.path.getmtime)
        return newest
    
    # Fallback to Desktop
    files = glob.glob(EXPORT_GLOB_DESKTOP)
    if not files:
        return None
    # Sort by modification time descending
    newest = max(files, key=os.path.getmtime)
    return newest


def _file_age_seconds(path: str) -> float:
    return time.time() - os.path.getmtime(path)


def _run_applescript_export() -> str:
    """Run the AppleScript exporter and return the path it prints."""
    try:
        if os.getenv("OF_RUNNER_V2") == "1":
            runner = pathlib.Path(__file__).resolve().parents[2] / "scripts" / "run_script.py"
            cmd = ["python3", str(runner), "--script", APPLE_SCRIPT_PATH]
        else:
            # -ss flag suppresses scripting addition result formatting (gives raw output)
            cmd = ["osascript", "-ss", APPLE_SCRIPT_PATH]

        result = subprocess.check_output(cmd)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"AppleScript export failed: {e}")

    # Clean stdout to get path
    path_str = result.decode().strip().strip("\"")
    if not path_str or not os.path.exists(path_str):
        # Fallback: scan again for newest file
        newest = _newest_export_path()
        if newest:
            return newest
        raise RuntimeError("Unable to determine export path after AppleScript run.")
    return path_str


def ensure_fresh_export(max_age_seconds: int = 1800) -> str:
    """Ensure a JSON export exists and is newer than max_age_seconds.

    Returns absolute path to the export file.
    Uses file-based caching to prevent multiple exports across command invocations.
    """
    current_time = time.time()
    cache = _load_cache()
    
    # Check if we have a cached result that's still valid
    if (cache["path"] and 
        cache["max_age"] == max_age_seconds and
        current_time - cache["timestamp"] < max_age_seconds):
        
        # Verify the cached file still exists and is fresh enough
        if os.path.exists(cache["path"]):
            file_age = _file_age_seconds(cache["path"])
            if file_age < max_age_seconds:
                return cache["path"]
    
    # Check for existing fresh export first
    newest = _newest_export_path()
    if newest and _file_age_seconds(newest) < max_age_seconds:
        # Cache this result
        cache["path"] = newest
        cache["timestamp"] = current_time
        cache["max_age"] = max_age_seconds
        _save_cache(cache)
        return newest

    # Need fresh export
    print("[ensure_export] Export too old or missing – triggering AppleScript export…", flush=True)
    new_path = _run_applescript_export()
    
    # Cache the new result
    cache["path"] = new_path
    cache["timestamp"] = current_time
    cache["max_age"] = max_age_seconds
    _save_cache(cache)
    
    return new_path


def clear_export_cache():
    """Clear the export cache. Useful for testing or when you want to force a fresh export."""
    if os.path.exists(CACHE_FILE):
        try:
            os.remove(CACHE_FILE)
        except OSError:
            pass 