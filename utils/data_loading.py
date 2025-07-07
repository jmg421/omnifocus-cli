import os
import sys
import json
from datetime import datetime, date
from typing import Optional, Any, Dict, List

def get_latest_json_export_path():
    files = [f for f in os.listdir('data') if f.startswith('omnifocus_export_') and f.endswith('.json')]
    if not files:
        return None
    files = [os.path.join('data', f) for f in files]
    files.sort(key=os.path.getmtime, reverse=True)
    return files[0]

def parse_cli_date(date_str: Optional[str]) -> Optional[date]:
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return None

def get_item_date(item_date_val: Optional[str]) -> Optional[date]:
    if not item_date_val:
        return None
    try:
        return datetime.fromisoformat(item_date_val.replace('Z', '+00:00')).date()
    except (ValueError, TypeError):
        try:
            return datetime.strptime(item_date_val, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            return None

def load_and_prepare_omnifocus_data(json_file_path: str) -> Dict[str, Any]:
    try:
        with open(json_file_path, 'r') as f:
            raw_data = json.load(f)
    except FileNotFoundError:
        print(f"Error: File not found at {json_file_path}", file=sys.stderr)
        return {}
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {json_file_path}", file=sys.stderr)
        return {}
    tasks_dict: Dict[str, Dict[str, Any]] = {}
    projects_dict: Dict[str, Dict[str, Any]] = {}
    folders_dict: Dict[str, Dict[str, Any]] = {}
    def process_task(task_data: Dict[str, Any], project_id: Optional[str] = None, parent_task_id: Optional[str] = None):
        if not task_data or not isinstance(task_data, dict) or not task_data.get('id'):
            return
        task_id = task_data['id']
        task_copy = task_data.copy()
        task_copy.setdefault('name', f'Unnamed Task {task_id}')
        if project_id:
            task_copy['projectId'] = project_id
        if parent_task_id:
            task_copy['parentId'] = parent_task_id
        task_copy['_source'] = 'project' if project_id else 'inbox'
        tasks_dict[task_id] = task_copy
        children = task_data.get("children", [])
        if isinstance(children, list):
            for child_task_data in children:
                process_task(child_task_data, project_id, parent_task_id=task_id)
    def process_project(project_data: Dict[str, Any], folder_id: Optional[str] = None):
        if not project_data or not isinstance(project_data, dict) or not project_data.get('id'):
            return
        project_id = project_data['id']
        project_copy = project_data.copy()
        project_copy.setdefault('name', f'Unnamed Project {project_id}')
        if folder_id:
            project_copy['folderId'] = folder_id
        projects_dict[project_id] = project_copy
        project_tasks_list = project_data.get("tasks", [])
        if isinstance(project_tasks_list, list):
            for task_data in project_tasks_list:
                process_task(task_data, project_id=project_id)
    def process_folder(folder_data: Dict[str, Any], parent_folder_id: Optional[str] = None):
        if not folder_data or not isinstance(folder_data, dict) or not folder_data.get('id'):
            return
        folder_id = folder_data['id']
        folder_copy = folder_data.copy()
        folder_copy.setdefault('name', f'Unnamed Folder {folder_id}')
        if parent_folder_id:
            folder_copy['parentFolderID'] = parent_folder_id
        folders_dict[folder_id] = folder_copy
        sub_folders_list = folder_data.get("folders", [])
        if isinstance(sub_folders_list, list):
            for sub_folder_data in sub_folders_list:
                process_folder(sub_folder_data, parent_folder_id=folder_id)
        folder_projects_list = folder_data.get("projects", [])
        if isinstance(folder_projects_list, list):
            for project_data in folder_projects_list:
                process_project(project_data, folder_id=folder_id)
    inbox_items_list = raw_data.get("inboxItems", [])
    if isinstance(inbox_items_list, list):
        for task_data in inbox_items_list:
            process_task(task_data)
    structure = raw_data.get("structure", {})
    if isinstance(structure, dict):
        top_level_projects_list = structure.get("topLevelProjects", [])
        if isinstance(top_level_projects_list, list):
            for project_data in top_level_projects_list:
                process_project(project_data)
        top_level_folders_list = structure.get("topLevelFolders", [])
        if isinstance(top_level_folders_list, list):
            for folder_data in top_level_folders_list:
                process_folder(folder_data)
    return {
        "all_tasks": list(tasks_dict.values()),
        "projects_map": projects_dict,
        "folders_map": folders_dict,
        "tags_map": raw_data.get("tags", {}),
    }

def query_prepared_data(
    prepared_data: Dict[str, Any],
    query_type: str, # "tasks", "projects", "folders"
    item_id_filter: Optional[str] = None,
    name_filter: Optional[str] = None,
    project_id_filter: Optional[str] = None, # For tasks
    folder_id_filter: Optional[str] = None,   # For projects
    status_filter: Optional[str] = None,
    due_before_filter: Optional[str] = None,
    due_after_filter: Optional[str] = None,
    defer_before_filter: Optional[str] = None,
    defer_after_filter: Optional[str] = None,
    completed_before_filter: Optional[str] = None,
    completed_after_filter: Optional[str] = None,
    tag_ids_all_filter: Optional[List[str]] = None, # Expecting a list of IDs
    tag_ids_any_filter: Optional[List[str]] = None  # Expecting a list of IDs
) -> List[Dict[str, Any]]:
    all_tasks: List[Dict[str, Any]] = prepared_data.get("all_tasks", [])
    projects_map: Dict[str, Dict[str, Any]] = prepared_data.get("projects_map", {})
    folders_map: Dict[str, Dict[str, Any]] = prepared_data.get("folders_map", {})
    results: List[Dict[str, Any]] = []
    due_before_date = parse_cli_date(due_before_filter)
    due_after_date = parse_cli_date(due_after_filter)
    defer_before_date = parse_cli_date(defer_before_filter)
    defer_after_date = parse_cli_date(defer_after_filter)
    completed_before_date = parse_cli_date(completed_before_filter)
    completed_after_date = parse_cli_date(completed_after_filter)
    tag_ids_all_set = set(tag_ids_all_filter) if tag_ids_all_filter else set()
    tag_ids_any_set = set(tag_ids_any_filter) if tag_ids_any_filter else set()
    if query_type == "tasks":
        for item in all_tasks:
            match = True
            if name_filter and not (name_filter.lower() in item.get("name", "").lower()):
                match = False; continue
            if project_id_filter and item.get("projectId") != project_id_filter:
                match = False; continue
            if status_filter and not (item.get("status", "").lower() == status_filter.lower()):
                match = False; continue
            item_due_date = get_item_date(item.get("dueDate"))
            if due_before_date and (not item_due_date or item_due_date >= due_before_date):
                match = False; continue
            if due_after_date and (not item_due_date or item_due_date <= due_after_date):
                match = False; continue
            item_defer_date = get_item_date(item.get("deferDate"))
            if defer_before_date and (not item_defer_date or item_defer_date >= defer_before_date):
                match = False; continue
            if defer_after_date and (not item_defer_date or item_defer_date <= defer_after_date):
                match = False; continue
            item_completed_date = get_item_date(item.get("completedDate"))
            if completed_before_date and (not item_completed_date or item_completed_date >= completed_before_date):
                match = False; continue
            if completed_after_date and (not item_completed_date or item_completed_date <= completed_after_date):
                match = False; continue
            item_tag_ids_set = set(item.get("tagIds", []))
            if tag_ids_all_set and not tag_ids_all_set.issubset(item_tag_ids_set):
                match = False; continue
            if tag_ids_any_set and not item_tag_ids_set.intersection(tag_ids_any_set):
                match = False; continue
            if match:
                results.append(item)
    elif query_type == "projects":
        for project_id, item in projects_map.items():
            match = True
            if name_filter and not (name_filter.lower() in item.get("name", "").lower()):
                match = False; continue
            if status_filter and not (item.get("status", "").lower() == status_filter.lower()):
                match = False; continue
            if match:
                results.append(item)
    elif query_type == "folders":
        for folder_id, item in folders_map.items():
            match = True
            if name_filter and not (name_filter.lower() in item.get("name", "").lower()):
                match = False; continue
            if status_filter and not (item.get("status", "").lower() == status_filter.lower()):
                match = False; continue
            if match:
                results.append(item)
    return results 