"""Pydantic models for Google Drive file/folder representations."""
from __future__ import annotations

from typing import Optional
from pydantic import BaseModel


class DriveFile(BaseModel):
    id: str
    name: str
    mimeType: str
    modifiedTime: str
    size: Optional[int] = None

    @property
    def is_folder(self) -> bool:
        return self.mimeType == "application/vnd.google-apps.folder"

    @property
    def is_csv(self) -> bool:
        return self.mimeType == "text/csv" or self.name.endswith(".csv")


class DriveFolder(BaseModel):
    id: str
    name: str
    files: list[DriveFile] = []
    subfolders: list["DriveFolder"] = []

    model_config = {"arbitrary_types_allowed": True}
