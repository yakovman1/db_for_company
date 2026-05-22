from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Literal

from pydantic import BaseModel, ConfigDict, Field


class LocationPayload(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    x: float
    y: float
    z: float


class DimensionsPayload(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    width: float | None = None
    height: float | None = None
    depth: float | None = None
    diameter: float | None = None


class OpeningItemPayload(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    element_unique_id: str = Field(alias="elementUniqueId", min_length=1)
    element_id: int = Field(alias="elementId")
    family_name: str = Field(alias="familyName")
    type_name: str = Field(alias="typeName")
    category_name: str = Field(alias="categoryName")
    level_name: str = Field(alias="levelName")
    location: LocationPayload
    dimensions: DimensionsPayload
    content_hash: str = Field(default="", alias="contentHash")
    extra_fields: Dict[str, Any] = Field(default_factory=dict, alias="extraFields")


class SyncOpeningsRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, protected_namespaces=())

    model_guid: uuid.UUID = Field(alias="modelGuid")
    model_name: str = Field(alias="modelName", min_length=1)
    schedule_name: str = Field(alias="scheduleName", min_length=1)
    soft_delete_missing: bool = Field(default=False, alias="softDeleteMissing")
    upsert_openings: bool = Field(default=True, alias="upsertOpenings")
    openings: List[OpeningItemPayload] = Field(default_factory=list)


SyncResultType = Literal["created", "updated", "softDeleted", "unchanged", "failed"]


class SyncOpeningItemResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)

    element_unique_id: str = Field(serialization_alias="elementUniqueId")
    result: SyncResultType
    opening_id: int | None = Field(default=None, serialization_alias="openingId")
    status: str | None = None


class SyncOpeningsResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)

    sync_id: uuid.UUID = Field(serialization_alias="syncId")
    created: int = 0
    updated: int = 0
    soft_deleted: int = Field(default=0, serialization_alias="softDeleted")
    unchanged: int = 0
    failed: int = 0
    items: List[SyncOpeningItemResult] = Field(default_factory=list)


class OpeningStatusItem(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)

    element_unique_id: str = Field(serialization_alias="elementUniqueId")
    opening_id: int = Field(serialization_alias="openingId")
    status: str
    schedule_name: str = Field(default="", serialization_alias="scheduleName")
    content_hash: str = Field(default="", serialization_alias="contentHash")
    updated_at: datetime = Field(serialization_alias="updatedAt")


class OpeningsListResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True, protected_namespaces=())

    model_guid: uuid.UUID = Field(serialization_alias="modelGuid")
    openings: List[OpeningStatusItem] = Field(default_factory=list)
