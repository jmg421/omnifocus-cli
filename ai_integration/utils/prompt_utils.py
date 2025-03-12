import os
import json
from pathlib import Path
from typing import Dict, Optional

def confirm_action(message: str) -> bool:
    """
    Prompts the user for a yes/no confirmation in the terminal.
    Returns True if user confirms, False otherwise.
    """
    response = input(f"{message} [y/N]: ").strip().lower()
    return response == "y"

def get_prompt_template(template_name: str, default_template: Optional[str] = None) -> str:
    """
    Get a prompt template by name from the templates directory.
    If the template doesn't exist, returns the default_template.
    """
    # Determine the templates directory
    module_dir = Path(__file__).parent.parent  # ai_integration directory
    templates_dir = module_dir / "prompt_templates"
    
    # Check if template file exists
    template_path = templates_dir / f"{template_name}.txt"
    if template_path.exists():
        with open(template_path, 'r') as f:
            return f.read()
    
    # Check if we have a sample prompts file with JSON templates
    sample_path = templates_dir / "sample_prompts.md"
    if sample_path.exists():
        with open(sample_path, 'r') as f:
            content = f.read()
            # Try to find template in markdown code blocks
            import re
            pattern = rf"```json\s*{{\s*\"name\":\s*\"{template_name}\"[^`]*```"
            matches = re.findall(pattern, content, re.DOTALL)
            if matches:
                # Extract the JSON from the first match
                json_str = matches[0].strip().replace("```json", "").replace("```", "").strip()
                try:
                    template_data = json.loads(json_str)
                    return template_data.get("prompt", default_template)
                except json.JSONDecodeError:
                    # If JSON parsing fails, fall back to default
                    pass
    
    # Return default template if provided, otherwise empty string
    return default_template or ""

def save_prompt_template(template_name: str, template_content: str) -> bool:
    """
    Save a prompt template to the templates directory.
    Returns True if successful, False otherwise.
    """
    # Determine the templates directory
    module_dir = Path(__file__).parent.parent  # ai_integration directory
    templates_dir = module_dir / "prompt_templates"
    
    # Create directory if it doesn't exist
    if not templates_dir.exists():
        templates_dir.mkdir(parents=True)
    
    # Save template
    template_path = templates_dir / f"{template_name}.txt"
    try:
        with open(template_path, 'w') as f:
            f.write(template_content)
        return True
    except Exception as e:
        print(f"Error saving template: {e}")
        return False

