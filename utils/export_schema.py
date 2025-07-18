from __future__ import annotations

from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field, Extra, validator


class TaskModel(BaseModel):
    id: str
    name: Optional[str] = None
    status: Optional[str] = None
    flagged: Optional[bool] = None
    dueDate: Optional[str] = None  # keep ISO string
    deferDate: Optional[str] = None
    completionDate: Optional[str] = None
    projectId: Optional[str] = None
    parentId: Optional[str] = None
    # allow other fields (notes, tags, etc.)

    class Config:
        extra = Extra.allow


class ProjectModel(BaseModel):
    id: str
    name: Optional[str] = None
    status: Optional[str] = None
    folderId: Optional[str] = None

    class Config:
        extra = Extra.allow


class FolderModel(BaseModel):
    id: str
    name: Optional[str] = None
    parentFolderID: Optional[str] = Field(None, alias="parentFolderId")

    class Config:
        extra = Extra.allow


class TagModel(BaseModel):
    id: str
    name: Optional[str] = None

    class Config:
        extra = Extra.allow


class ExportModel(BaseModel):
    tasks: List[TaskModel]
    inboxTasks: Optional[List[TaskModel]] = []
    projects: Dict[str, ProjectModel]
    folders: Dict[str, FolderModel] = {}
    tags: Dict[str, TagModel] = {}

    class Config:
        extra = Extra.allow

    @validator("projects", "folders", pre=True)
    def ensure_dict(cls, v):  # noqa D401
        """Allow list input but convert to dict keyed by id."""
        if isinstance(v, list):
            return {item.get("id"): item for item in v if item.get("id")}
        return v 