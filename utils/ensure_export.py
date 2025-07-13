"""ensure_export.py
Utility for omni-cli: guarantee a recent OmniFocus JSON export is available.

• Looks for files matching ~/Desktop/omnifocus-export-*.json (created by the AppleScript).
• If none exist or the newest is older than `max_age_seconds`, it runs the AppleScript exporter
  (which copies the path to stdout) and returns that path.

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
from typing import Optional

# Relative path from repo root to AppleScript
APPLE_SCRIPT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "OmniFocus-MCP",
    "scripts",
    "auto_export_master_plan.applescript",
)

# Glob pattern for exported JSON files (user Desktop)
EXPORT_GLOB = os.path.expanduser("~/Desktop/omnifocus-export-*.json")


def _newest_export_path() -> Optional[str]:
    """Return newest export file path or None if none exist."""
    files = glob.glob(EXPORT_GLOB)
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
        # -ss flag suppresses scripting addition result formatting (gives raw output)
        result = subprocess.check_output([
            "osascript",
            "-ss",
            APPLE_SCRIPT_PATH,
        ])
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
    """
    newest = _newest_export_path()
    if newest and _file_age_seconds(newest) < max_age_seconds:
        return newest

    # Need fresh export
    print("[ensure_export] Export too old or missing – triggering AppleScript export…", flush=True)
    return _run_applescript_export() 