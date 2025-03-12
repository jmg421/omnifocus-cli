"""Utility functions for OmniFocus API."""

def escape_applescript_string(text: str) -> str:
    """Escape special characters for AppleScript strings."""
    if not text:
        return ""
    return text.replace('"', '\\"').replace('\\', '\\\\') 