#!/usr/bin/env python3
"""
This script patches imports in command files and other relevant files
to use relative paths instead of omnifocus_cli.* imports.
"""

import os
import re
import glob
from pathlib import Path

def patch_file(file_path):
    """Patch imports in a single file"""
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Replace omnifocus_cli.X with X
    modified_content = re.sub(
        r'from\s+omnifocus_cli\.([^.]+)', 
        r'from \1', 
        content
    )
    
    # Replace omnifocus_cli.X.Y with X.Y
    modified_content = re.sub(
        r'from\s+omnifocus_cli\.([^.]+)\.([^.]+)', 
        r'from \1.\2', 
        content
    )
    
    # Replace import X with import X
    modified_content = re.sub(
        r'import\s+omnifocus_cli\.([^.]+)', 
        r'import \1', 
        content
    )
    
    if content != modified_content:
        with open(file_path, 'w') as f:
            f.write(modified_content)
        return True
    
    return False

def main():
    """Patch imports in all relevant Python files"""
    # Get all Python files in the project
    python_files = glob.glob("**/*.py", recursive=True)
    
    patched_files = []
    for file_path in python_files:
        if patch_file(file_path):
            patched_files.append(file_path)
    
    if patched_files:
        print(f"Patched imports in {len(patched_files)} files:")
        for file in patched_files:
            print(f"  - {file}")
    else:
        print("No files needed patching.")

if __name__ == "__main__":
    main() 