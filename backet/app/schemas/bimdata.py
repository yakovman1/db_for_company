from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Literal

from pydantic import BaseModel, ConfigDict, Field

SUPPORTED_SCHEMA_VERSION = "1.0"


class ErrorResponse(BaseModel):
    error_code: str = Field(serialization_alias="errorCode")
    message: str


class BimdataSource(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    plugin_id: str = Field(alias="pluginId", min_length=1)
    plugin_version: str = Field(alias="pluginVersion", min_length=1)
    company_id: str = Field(alias="companyId", min_length=1)
    windows_user: str = Field(alias="windowsUser", min_length=1)


class SnapshotPayload(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    snapshot_date: datetime
    model_name: str = Field(min_length=1)
    revit_version: int
    pbp_x: float | None = None
    pbp_y: float | None = None
    pbp_z: float | None = None
    pbp_angle: float | None = None
    sp_x: float | None = None
    sp_y: float | None = None
    sp_z: float | None = None
    fop_name: str | None = None
    fop_path: str | None = None
    project_number: str | None = None
    project_name: str | None = None
    project_stage: str | None = None
    worksets_json: List[Dict[str, Any]] = Field(default_factory=list)
    linked_files_json: List[Dict[str, Any]] = Field(default_factory=list)


class CreateSnapshotRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    schema_version: str = Field(alias="schemaVersion")
    source: BimdataSource
    snapshot: SnapshotPayload


SnapshotStatus = Literal["created", "completed", "failed"]


class SnapshotStatusResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)

    snapshot_id: uuid.UUID = Field(serialization_alias="snapshotId")
    status: SnapshotStatus


class LocationPoint(BaseModel):
    x: float
    y: float
    z: float


class ConnectorPayload(BaseModel):
    connector_id: int | None = None
    direction: str | None = None
    xyz: List[float] = Field(default_factory=list, min_length=3, max_length=3)
    is_connected: bool | None = None
    connected_to_guid: str | None = None


class MepElementPayload(BaseModel):
    snapshot_date: datetime
    element_guid: str = Field(min_length=1)
    revit_id: int | None = None
    category_name: str | None = None
    family_name: str | None = None
    type_name: str | None = None
    workset_name: str | None = None
    level_guid: str | None = None
    level_name: str | None = None
    space_guid: str | None = None
    system_classification: str | None = None
    system_name: str | None = None
    is_linear: bool = False
    length: float | None = None
    dimension_1: float | None = None
    dimension_2: float | None = None
    location_point: LocationPoint | None = None
    bounding_box_volume: float | None = None
    bep_parameters: Dict[str, Any] = Field(default_factory=dict)
    connectors_json: List[ConnectorPayload] = Field(default_factory=list)


class ElementsBatchRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    schema_version: str = Field(alias="schemaVersion")
    batch_index: int = Field(alias="batchIndex", ge=0)
    is_last_batch: bool = Field(alias="isLastBatch")
    elements: List[MepElementPayload] = Field(default_factory=list)


class BatchResponse(BaseModel):
    accepted: int
    rejected: int
    errors: List[str] = Field(default_factory=list)


class CompleteSnapshotRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    total_elements: int = Field(alias="totalElements", ge=0)
    total_batches: int = Field(alias="totalBatches", ge=0)


class FailSnapshotRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    error_code: str = Field(alias="errorCode", min_length=1)
    message: str = Field(min_length=1)

