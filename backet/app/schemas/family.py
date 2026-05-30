from __future__ import annotations

import re
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

HEX_RE = re.compile(r"^[0-9a-fA-F]+$")


class InitUploadRequest(BaseModel):
    original_filename: str = Field(min_length=1, max_length=255)
    size_bytes: int | None = Field(default=None, ge=0)
    sha256: str | None = Field(default=None, min_length=8, max_length=128)
    family_name: str | None = Field(default=None, max_length=512)
    category: str | None = Field(default=None, max_length=255)
    is_primary: bool | None = None
    parent_family_id: uuid.UUID | None = None

    @field_validator("sha256")
    @classmethod
    def validate_sha256(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if not HEX_RE.match(v):
            raise ValueError("sha256 must be hex")
        return v.lower()


class InitUploadResponse(BaseModel):
    family_id: uuid.UUID
    version: int = 1
    is_new: bool = True
    unchanged: bool = False
    bucket: str
    object_key: str
    presigned_put_url: str | None = None
    thumbnail_object_key: str | None = None
    presigned_thumbnail_put_url: str | None = None
    expires_in_seconds: int


class FamilyParameterPayload(BaseModel):
    name: str
    is_instance: bool = False
    is_shared: bool = False
    shared_guid: str | None = None
    storage_type: str | None = None
    spec: str | None = None


class FamilyTypeValuePayload(BaseModel):
    type_name: str
    values: Dict[str, Any]


class FamilyMetadataPayload(BaseModel):
    family_name: str | None = None
    category: str | None = None
    parameters: List[FamilyParameterPayload] = Field(default_factory=list)
    types: List[FamilyTypeValuePayload] = Field(default_factory=list)
    extra: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("parameters")
    @classmethod
    def ensure_unique_params(cls, v: List[FamilyParameterPayload]) -> List[FamilyParameterPayload]:
        seen = set()
        for item in v:
            if item.name in seen:
                raise ValueError(f"duplicate parameter {item.name}")
            seen.add(item.name)
        return v


class MetadataRequest(BaseModel):
    metadata: FamilyMetadataPayload


class CompleteUploadRequest(BaseModel):
    etag: str | None = None
    uploaded_at: datetime | None = None


class FamilySummary(BaseModel):
    id: uuid.UUID
    version: int = 1
    project_id: uuid.UUID
    status: str
    bucket: str
    object_key: str
    original_filename: str
    sha256: str | None = None
    size_bytes: int | None = None
    family_name: str | None = None
    category: str | None = None
    is_primary: bool | None = None
    parent_family_id: uuid.UUID | None = None
    has_thumbnail: bool = False
    metadata_json: Dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime
    uploaded_at: datetime | None = None
    etag: str | None = None

    class Config:
        from_attributes = True


class ListFamiliesResponse(BaseModel):
    items: List[FamilySummary]
    total: int


class DownloadUrlResponse(BaseModel):
    presigned_get_url: str
    expires_in_seconds: int


class FavoriteItem(BaseModel):
    family_id: uuid.UUID
    created_at: datetime

    class Config:
        from_attributes = True


class FavoritesListResponse(BaseModel):
    items: List[FavoriteItem]


class AddFavoriteRequest(BaseModel):
    family_id: uuid.UUID

