"""
Placeholder for using OmniFocus OmniJS (Omni Automation) instead of AppleScript.

If you choose to use OmniJS, you can evaluate JavaScript in OmniFocus by calling:
    osascript -l JavaScript

or using AppleScript's 'evaluate javascript' command.
"""

import subprocess

def run_omnijs(script_text: str) -> str:
    """
    Runs the provided JS code inside OmniFocus using an AppleScript shell.
    Returns the script's output as a string, or empty if there's an error.
    """
    as_script = f'''
    tell application "OmniFocus"
        try
            set jsResult to evaluate javascript "{script_text}"
            return jsResult
        on error errMsg
            return ""
        end try
    end tell
    '''
    result = subprocess.run(["osascript", "-e", as_script], capture_output=True, text=True)
    if result.returncode == 0:
        return result.stdout.strip()
    return ""

