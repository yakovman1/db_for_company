from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List

from fastapi import HTTPException, status

from app.core.config import get_settings
from app.core.logging import get_logger
import app.db.repositories as repo
from app.db.models import Family, FamilyStatus
from app.schemas.auth import PluginUserContext
from app.schemas.family import (
    CompleteUploadRequest,
    FamilyMetadataPayload,
    InitUploadRequest,
    InitUploadResponse,
)
from app.services import auth as auth_service
from app.services.s3 import s3_service
from app.utils.filename import sanitize_filename

logger = get_logger(__name__)
settings = get_settings()


async def _project_id_for_user(session, user: PluginUserContext) -> uuid.UUID:
    return await auth_service.resolve_company_project_id(session, user.company_id)


def _ensure_family_access(user: PluginUserContext, family: Family, project_id: uuid.UUID) -> None:
    if family.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Family access denied")


def _build_object_key(project_id: uuid.UUID, family_id: uuid.UUID, sha256: str | None, original_filename: str) -> str:
    suffix = ""
    if sha256:
        suffix = f"{sha256.lower()}.rfa"
    else:
        safe_name = sanitize_filename(original_filename)
        if not safe_name.lower().endswith(".rfa"):
            safe_name = f"{safe_name}.rfa"
        suffix = safe_name
    return f"projects/{project_id}/families/{family_id}/{suffix}"


async def init_upload(user: PluginUserContext, payload: InitUploadRequest, session) -> InitUploadResponse:
    project_id = await _project_id_for_user(session, user)

    family_id = uuid.uuid4()
    object_key = _build_object_key(project_id, family_id, payload.sha256, payload.original_filename)
    family = await repo.create_family(
        session,
        family_id=family_id,
        project_id=project_id,
        bucket=settings.minio_bucket,
        object_key=object_key,
        original_filename=payload.original_filename,
        sha256=payload.sha256,
        size_bytes=payload.size_bytes,
    )

    presigned_put_url = s3_service.generate_put_url(object_key, expires_in=settings.presigned_put_expires)
    return InitUploadResponse(
        family_id=family.id,
        bucket=family.bucket,
        object_key=family.object_key,
        presigned_put_url=presigned_put_url,
        expires_in_seconds=settings.presigned_put_expires,
    )


def _flatten_parameters(metadata: FamilyMetadataPayload) -> tuple[List[dict], List[dict]]:
    params = [
        {
            "name": p.name,
            "is_instance": p.is_instance,
            "is_shared": p.is_shared,
            "shared_guid": p.shared_guid,
            "storage_type": p.storage_type,
            "spec": p.spec,
        }
        for p in metadata.parameters
    ]

    type_values: List[dict] = []
    for t in metadata.types:
        for param_name, value in t.values.items():
            type_values.append({"type_name": t.type_name, "param_name": param_name, "value_text": str(value)})
    return params, type_values


async def save_metadata(user: PluginUserContext, family_id: uuid.UUID, metadata: FamilyMetadataPayload, session) -> Family:
    project_id = await _project_id_for_user(session, user)
    family = await repo.get_family(session, family_id)
    if not family:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Family not found")

    _ensure_family_access(user, family, project_id)
    params, type_values = _flatten_parameters(metadata)
    metadata_dict = metadata.model_dump()
    return await repo.update_metadata(
        session,
        family=family,
        metadata_json=metadata_dict,
        parameters=params,
        type_values=type_values,
    )


async def complete_upload(user: PluginUserContext, family_id: uuid.UUID, payload: CompleteUploadRequest, session) -> Family:
    project_id = await _project_id_for_user(session, user)
    family = await repo.get_family(session, family_id)
    if not family:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Family not found")
    _ensure_family_access(user, family, project_id)

    etag = payload.etag
    uploaded_at = payload.uploaded_at
    size_bytes = None

    head = s3_service.head_object(family.object_key)
    if head:
        etag = etag or head.get("ETag", "").strip('"')
        uploaded_at = uploaded_at or head.get("LastModified")
        size_bytes = head.get("ContentLength")
    if uploaded_at and isinstance(uploaded_at, datetime) and uploaded_at.tzinfo is None:
        uploaded_at = uploaded_at.replace(tzinfo=timezone.utc)

    status_to_set = FamilyStatus.READY if head or payload.etag else FamilyStatus.UPLOADED

    return await repo.mark_ready(
        session, family=family, etag=etag, uploaded_at=uploaded_at, size_bytes=size_bytes, status=status_to_set
    )


async def get_family(user: PluginUserContext, family_id: uuid.UUID, session) -> Family:
    project_id = await _project_id_for_user(session, user)
    family = await repo.get_family(session, family_id)
    if not family:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Family not found")
    _ensure_family_access(user, family, project_id)
    return family


async def list_families(
    user: PluginUserContext,
    limit: int,
    offset: int,
    session,
    *,
    is_primary: bool | None = None,
    parent_id: uuid.UUID | None = None,
):
    project_id = await _project_id_for_user(session, user)
    families = await repo.list_families_by_project(
        session, project_id=project_id, limit=limit, offset=offset, is_primary=is_primary, parent_id=parent_id
    )
    total = await repo.count_families_by_project(
        session, project_id=project_id, is_primary=is_primary, parent_id=parent_id
    )
    return families, total


async def get_download_url(user: PluginUserContext, family_id: uuid.UUID, session) -> str:
    project_id = await _project_id_for_user(session, user)
    family = await repo.get_family(session, family_id)
    if not family:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Family not found")
    _ensure_family_access(user, family, project_id)
    return s3_service.generate_get_url(family.object_key, expires_in=settings.presigned_get_expires)
