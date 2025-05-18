import json
import sys

def transform_task(task_data_orig, all_tasks_orig):
    """Transforms a single task and its children from omni-js format to ofcli format."""
    task_transformed = {
        "type": "Task",
        "id": task_data_orig.get("id"),
        "name": task_data_orig.get("name"),
        "note": task_data_orig.get("note", ""),
        "completed": task_data_orig.get("status") == "Completed" or task_data_orig.get("completedDate") is not None,
        "flagged": task_data_orig.get("flagged", False),
        "estimatedMinutes": task_data_orig.get("estimatedMinutes"),
        "dueDate": task_data_orig.get("dueDate"),
        "deferDate": task_data_orig.get("deferDate"),
        "completedDate": task_data_orig.get("completedDate"),
        # "parentId" is not directly used in the target 'ofcli' structure's task items,
        # nesting is via the 'children' list.
    }

    children_transformed = []
    child_ids = task_data_orig.get("childIds", [])
    if child_ids:
        for child_id in child_ids:
            # Find the child task in the original flat list of all tasks
            child_task_orig = next((t for t in all_tasks_orig if t.get("id") == child_id), None)
            if child_task_orig:
                children_transformed.append(transform_task(child_task_orig, all_tasks_orig))
    
    if children_transformed:
        task_transformed["children"] = children_transformed
    
    # Add other relevant fields if necessary, e.g., tagIds, but ofcli format might not use them directly
    # task_transformed["tagIds"] = task_data_orig.get("tagIds", [])
    return task_transformed

def transform_project(project_data_orig, all_tasks_orig):
    """Transforms a single project and its tasks from omni-js format to ofcli format."""
    project_transformed = {
        "type": "Project",
        "id": project_data_orig.get("id"),
        "name": project_data_orig.get("name"),
        "folderId": project_data_orig.get("folderID"), # Keep folderID for context if needed
        "completed": project_data_orig.get("status") == "Completed" or project_data_orig.get("completedDate") is not None,
        "dueDate": project_data_orig.get("dueDate"),
        "deferDate": project_data_orig.get("deferDate"),
        "completedDate": project_data_orig.get("completedDate"),
        "note": project_data_orig.get("note", ""),
        "tasks": [] # ofcli expects a list of tasks
    }

    # Find top-level tasks for this project
    if all_tasks_orig:
        for task_orig in all_tasks_orig:
            if task_orig.get("projectId") == project_transformed["id"] and task_orig.get("parentId") is None:
                project_transformed["tasks"].append(transform_task(task_orig, all_tasks_orig))
    
    return project_transformed

def transform_folder(folder_data_orig, all_projects_orig_dict, all_tasks_orig):
    """Transforms a single folder and its contents from omni-js format to ofcli format."""
    folder_transformed = {
        "type": "Folder",
        "id": folder_data_orig.get("id"),
        "name": folder_data_orig.get("name"),
        "projects": [],
        "folders": [] # For nested folders
    }

    # Find projects belonging to this folder
    if all_projects_orig_dict:
        for project_id, project_orig in all_projects_orig_dict.items():
            if project_orig.get("folderID") == folder_transformed["id"]:
                folder_transformed["projects"].append(transform_project(project_orig, all_tasks_orig))
    
    # Note: Handling nested folders (folder_data_orig containing other folders)
    # The omni-js dump seems to have a flat list/dict of folders at the root.
    # If parentFolderID is used for nesting, that logic would go here to find child folders.
    # For now, assuming a flat folder structure from the input that maps to topLevelFolders.
    # If sub-folders are found via parentFolderID, they should be appended to folder_transformed["folders"].

    return folder_transformed

def main(input_file_path, output_file_path):
    try:
        with open(input_file_path, 'r') as f:
            data_orig = json.load(f)
    except FileNotFoundError:
        print(f"Error: Input file not found at {input_file_path}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {input_file_path}", file=sys.stderr)
        sys.exit(1)

    if not isinstance(data_orig, dict):
        print("Error: Original JSON is not a dictionary.", file=sys.stderr)
        sys.exit(1)

    all_tasks_orig = data_orig.get("tasks", []) # Expected to be a list
    all_projects_orig_dict = data_orig.get("projects", {}) # Expected to be a dict
    all_folders_orig_dict = data_orig.get("folders", {})   # Expected to be a dict

    transformed_data = {
        "structure": {
            "topLevelFolders": [],
            "topLevelProjects": [],
            # ofcli format might also support loose tasks directly under structure,
            # but current transformation focuses on folders & projects.
            # "tasks": [] 
        }
    }

    # Process folders
    for folder_id, folder_orig in all_folders_orig_dict.items():
        # Assuming all folders in the omni-js dump are top-level for the ofcli structure
        # unless a parentFolderID is present and we implement nesting.
        if not folder_orig.get("parentFolderID"): # Consider folders without a parent as top-level
            transformed_folder = transform_folder(folder_orig, all_projects_orig_dict, all_tasks_orig)
            transformed_data["structure"]["topLevelFolders"].append(transformed_folder)

    # Process projects that are not in any folder (top-level projects)
    for project_id, project_orig in all_projects_orig_dict.items():
        if not project_orig.get("folderID"): # folderID is null or missing
            transformed_project = transform_project(project_orig, all_tasks_orig)
            transformed_data["structure"]["topLevelProjects"].append(transformed_project)
    
    # Optional: Process loose tasks (tasks not belonging to any project)
    # if all_tasks_orig:
    #     for task_orig in all_tasks_orig:
    #         if not task_orig.get("projectId") and not task_orig.get("parentId"):
    #             # These are truly loose tasks, not part of a project hierarchy
    #             transformed_data["structure"].setdefault("tasks", []).append(transform_task(task_orig, all_tasks_orig))


    try:
        with open(output_file_path, 'w') as f:
            json.dump(transformed_data, f, indent=2)
        print(f"Successfully transformed JSON written to {output_file_path}")
    except IOError:
        print(f"Error: Could not write to output file {output_file_path}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python transform_omnijs_to_ofcli.py <input_json_path> <output_json_path>", file=sys.stderr)
        sys.exit(1)
    
    input_path = sys.argv[1]
    output_path = sys.argv[2]
    main(input_path, output_path) 