from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class FamilyLogEntryIn(BaseModel):
    """Клиентское событие — принимается в POST /families/logs."""
    action: str
    outcome: str = "success"
    family_id: uuid.UUID | None = None
    family_name: str | None = None
    original_filename: str | None = None
    category: str | None = None
    family_version: int | None = None
    is_primary: bool | None = None
    parent_family_id: uuid.UUID | None = None
    revit_project_name: str | None = None
    revit_project_path: str | None = None
    revit_document_kind: str | None = None
    error_message: str | None = None
    http_status: int | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class PostLogsRequest(BaseModel):
    entries: list[FamilyLogEntryIn] = Field(..., min_length=1, max_length=100)


class FamilyLogEntry(BaseModel):
    """Запись журнала — возвращается в GET /families/logs."""
    model_config = {"from_attributes": True}

    id: uuid.UUID
    created_at: datetime
    company_id: str
    windows_user: str
    action: str
    outcome: str
    source: str
    family_id: uuid.UUID | None = None
    family_name: str | None = None
    original_filename: str | None = None
    category: str | None = None
    family_version: int | None = None
    is_primary: bool | None = None
    parent_family_id: uuid.UUID | None = None
    catalog_project_id: uuid.UUID | None = None
    revit_project_name: str | None = None
    revit_project_path: str | None = None
    revit_document_kind: str | None = None
    error_message: str | None = None
    http_status: int | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class GetLogsResponse(BaseModel):
    items: list[FamilyLogEntry]
