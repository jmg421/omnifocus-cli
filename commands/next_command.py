import subprocess
import os
import json
from typing import Dict, Any

def format_next_actions(report: Dict[str, Any]) -> str:
    """Formats the JSON report from getNextActionsReport into a readable string."""
    output = ["--- Next Actions ---"]
    
    if not report.get('tasks'):
        return "No next actions found."

    for task in report['tasks']:
        task_name = task.get('name', 'Unnamed Task')
        project_name = task.get('projectName', 'No Project')
        due_date = task.get('dueDate', 'No due date')
        
        line = f"- {task_name} (Project: {project_name}"
        if due_date != 'No due date':
            line += f", Due: {due_date}"
        line += ")"
        output.append(line)
        
    return "\n".join(output)

def handle_next(args):
    """
    Calls the getNextActionsReport tool via node and displays the results.
    """
    # Build the path to the compiled JavaScript tool
    script_path = os.path.abspath(os.path.join(
        os.path.dirname(__file__), 
        '../../OmniFocus-MCP/dist/tools/definitions/getNextActionsReport.js'
    ))

    if not os.path.exists(script_path):
        print(f"Error: The required tool script was not found at {script_path}")
        print("Please ensure you have built the OmniFocus-MCP project.")
        return

    # Note: This tool currently takes no arguments from the Python side,
    # but we could add them here if needed by passing a JSON file.
    cmd = ['node', script_path]
    
    try:
        # The tool needs to be run from its own directory to find node_modules
        mcp_root_path = os.path.abspath(os.path.join(
            os.path.dirname(__file__), 
            '../../OmniFocus-MCP'
        ))
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            check=True, 
            cwd=mcp_root_path
        )
        
        # The output is a JSON string within a larger JSON structure.
        # We need to parse the outer structure first.
        response_json = json.loads(result.stdout)
        
        # The actual task data is a JSON string inside the 'text' field.
        report_json_str = response_json['content'][0]['text']
        report = json.loads(report_json_str)
        
        # Format and print the report
        formatted_output = format_next_actions(report)
        print(formatted_output)

    except subprocess.CalledProcessError as e:
        print("Error running getNextActionsReport tool:")
        print(e.stderr.strip())
    except (json.JSONDecodeError, KeyError, IndexError) as e:
        print(f"Error parsing the output from the tool: {e}")
        print("Raw output:")
        print(result.stdout) 