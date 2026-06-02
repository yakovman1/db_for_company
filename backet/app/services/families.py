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


async def _catalog_project_id(session) -> uuid.UUID:
    """Rev 7: единый каталог — project_id не зависит от JWT company_id."""
    return await auth_service.resolve_shared_catalog_project_id(session)


def _ensure_family_access(user: PluginUserContext, family: Family, project_id: uuid.UUID) -> None:
    if family.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Family access denied")


def _build_object_key(project_id: uuid.UUID, family_id: uuid.UUID, sha256: str | None, original_filename: str, *, stable: bool = False) -> str:
    if stable:
        return f"projects/{project_id}/families/{family_id}/family.rfa"
    suffix = ""
    if sha256:
        suffix = f"{sha256.lower()}.rfa"
    else:
        safe_name = sanitize_filename(original_filename)
        if not safe_name.lower().endswith(".rfa"):
            safe_name = f"{safe_name}.rfa"
        suffix = safe_name
    return f"projects/{project_id}/families/{family_id}/{suffix}"


def _build_thumbnail_key(project_id: uuid.UUID, family_id: uuid.UUID) -> str:
    return f"projects/{project_id}/families/{family_id}/thumbnail.png"


def _thumbnail_urls_for(project_id: uuid.UUID, family_id: uuid.UUID, is_primary: bool | None) -> tuple[str | None, str | None]:
    """Возвращает (thumbnail_object_key, presigned_thumbnail_put_url) только для host-семейств."""
    if not is_primary:
        return None, None
    key = _build_thumbnail_key(project_id, family_id)
    url = s3_service.generate_put_url(key, expires_in=settings.presigned_put_expires, content_type="image/png")
    return key, url


async def init_upload(user: PluginUserContext, payload: InitUploadRequest, session) -> InitUploadResponse:
    project_id = await _catalog_project_id(session)
    has_identity = payload.family_name is not None and payload.category is not None and payload.is_primary is not None

    if has_identity:
        existing = await repo.find_family_by_identity(
            session,
            project_id=project_id,
            family_name=payload.family_name,  # type: ignore[arg-type]
            category=payload.category,  # type: ignore[arg-type]
            is_primary=payload.is_primary,  # type: ignore[arg-type]
            parent_family_id=payload.parent_family_id,
        )

        if existing is not None:
            if payload.sha256 and existing.sha256 == payload.sha256:
                # Файл не изменился — но для host всё равно выдаём thumbnail presigned URL
                thumb_key, thumb_url = _thumbnail_urls_for(project_id, existing.id, existing.is_primary)
                logger.info("init_upload_unchanged", family_id=str(existing.id), version=existing.version,
                            company_id=user.company_id, windows_user=user.windows_user)
                return InitUploadResponse(
                    family_id=existing.id,
                    version=existing.version,
                    is_new=False,
                    unchanged=True,
                    bucket=existing.bucket,
                    object_key=existing.object_key,
                    presigned_put_url=None,
                    thumbnail_object_key=thumb_key,
                    presigned_thumbnail_put_url=thumb_url,
                    expires_in_seconds=settings.presigned_put_expires if thumb_url else 0,
                )

            object_key = _build_object_key(project_id, existing.id, payload.sha256, payload.original_filename, stable=True)
            family = await repo.increment_version(
                session,
                family=existing,
                sha256=payload.sha256,
                size_bytes=payload.size_bytes,
                original_filename=payload.original_filename,
                object_key=object_key,
            )
            presigned_put_url = s3_service.generate_put_url(object_key, expires_in=settings.presigned_put_expires)
            thumb_key, thumb_url = _thumbnail_urls_for(project_id, family.id, payload.is_primary)
            logger.info("init_upload_version", family_id=str(family.id), version=family.version,
                        company_id=user.company_id, windows_user=user.windows_user)
            return InitUploadResponse(
                family_id=family.id,
                version=family.version,
                is_new=False,
                unchanged=False,
                bucket=family.bucket,
                object_key=family.object_key,
                presigned_put_url=presigned_put_url,
                thumbnail_object_key=thumb_key,
                presigned_thumbnail_put_url=thumb_url,
                expires_in_seconds=settings.presigned_put_expires,
            )

        family_id = uuid.uuid4()
        object_key = _build_object_key(project_id, family_id, payload.sha256, payload.original_filename, stable=True)
        family = await repo.create_family(
            session,
            family_id=family_id,
            project_id=project_id,
            bucket=settings.minio_bucket,
            object_key=object_key,
            original_filename=payload.original_filename,
            sha256=payload.sha256,
            size_bytes=payload.size_bytes,
            family_name=payload.family_name,
            category=payload.category,
            is_primary=payload.is_primary,
            parent_family_id=payload.parent_family_id,
            version=1,
        )
        presigned_put_url = s3_service.generate_put_url(object_key, expires_in=settings.presigned_put_expires)
        thumb_key, thumb_url = _thumbnail_urls_for(project_id, family.id, payload.is_primary)
        logger.info("init_upload_new", family_id=str(family.id),
                    company_id=user.company_id, windows_user=user.windows_user)
        return InitUploadResponse(
            family_id=family.id,
            version=family.version,
            is_new=True,
            unchanged=False,
            bucket=family.bucket,
            object_key=family.object_key,
            presigned_put_url=presigned_put_url,
            thumbnail_object_key=thumb_key,
            presigned_thumbnail_put_url=thumb_url,
            expires_in_seconds=settings.presigned_put_expires,
        )

    # --- legacy: нет identity-полей, создаём запись как раньше ---
    family_id = uuid.uuid4()
    object_key = _build_object_key(project_id, family_id, payload.sha256, payload.original_filename, stable=False)
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
        version=family.version,
        is_new=True,
        unchanged=False,
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
    project_id = await _catalog_project_id(session)
    family = await repo.get_family(session, family_id)
    if not family:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Family not found")

    _ensure_family_access(user, family, project_id)
    params, type_values = _flatten_parameters(metadata)
    metadata_dict = metadata.model_dump()

    # Rev 7: аудит — перезаписываем/дополняем extra из JWT (authoritative)
    if "extra" not in metadata_dict or metadata_dict["extra"] is None:
        metadata_dict["extra"] = {}
    metadata_dict["extra"]["uploaded_by_company_id"] = user.company_id
    metadata_dict["extra"]["uploaded_by_windows_user"] = user.windows_user
    metadata_dict["extra"]["uploaded_at"] = datetime.now(timezone.utc).isoformat()

    logger.info("save_metadata", family_id=str(family_id),
                company_id=user.company_id, windows_user=user.windows_user)
    return await repo.update_metadata(
        session,
        family=family,
        metadata_json=metadata_dict,
        parameters=params,
        type_values=type_values,
    )


async def complete_upload(user: PluginUserContext, family_id: uuid.UUID, payload: CompleteUploadRequest, session) -> Family:
    project_id = await _catalog_project_id(session)
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

    has_thumbnail = False
    if family.is_primary:
        thumb_key = _build_thumbnail_key(project_id, family.id)
        has_thumbnail = s3_service.head_object(thumb_key) is not None

    status_to_set = FamilyStatus.READY if head or payload.etag else FamilyStatus.UPLOADED

    result = await repo.mark_ready(
        session,
        family=family,
        etag=etag,
        uploaded_at=uploaded_at,
        size_bytes=size_bytes,
        has_thumbnail=has_thumbnail,
        status=status_to_set,
    )
    logger.info("complete_upload", family_id=str(family_id), status=status_to_set.value, has_thumbnail=has_thumbnail,
                company_id=user.company_id, windows_user=user.windows_user)
    return result


async def get_family(user: PluginUserContext, family_id: uuid.UUID, session) -> Family:
    project_id = await _catalog_project_id(session)
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
    project_id = await _catalog_project_id(session)
    families = await repo.list_families_by_project(
        session, project_id=project_id, limit=limit, offset=offset, is_primary=is_primary, parent_id=parent_id
    )
    total = await repo.count_families_by_project(
        session, project_id=project_id, is_primary=is_primary, parent_id=parent_id
    )
    return families, total


async def get_download_url(user: PluginUserContext, family_id: uuid.UUID, session) -> str:
    project_id = await _catalog_project_id(session)
    family = await repo.get_family(session, family_id)
    if not family:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Family not found")
    _ensure_family_access(user, family, project_id)
    logger.info("download_url", family_id=str(family_id),
                company_id=user.company_id, windows_user=user.windows_user)
    return s3_service.generate_get_url(family.object_key, expires_in=settings.presigned_get_expires)


async def get_thumbnail_url(user: PluginUserContext, family_id: uuid.UUID, session) -> str:
    project_id = await _catalog_project_id(session)
    family = await repo.get_family(session, family_id)
    if not family:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Family not found")
    _ensure_family_access(user, family, project_id)
    if not family.has_thumbnail:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thumbnail not available")
    thumb_key = _build_thumbnail_key(project_id, family.id)
    head = s3_service.head_object(thumb_key)
    if not head:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thumbnail not available")
    return s3_service.generate_get_url(thumb_key, expires_in=settings.presigned_get_expires)


async def thumbnail_init_upload(user: PluginUserContext, family_id: uuid.UUID, session):
    from app.schemas.family import ThumbnailInitUploadResponse
    project_id = await _catalog_project_id(session)
    family = await repo.get_family(session, family_id)
    if not family:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Family not found")
    _ensure_family_access(user, family, project_id)
    thumb_key = _build_thumbnail_key(project_id, family.id)
    url = s3_service.generate_put_url(thumb_key, expires_in=settings.presigned_put_expires, content_type="image/png")
    return ThumbnailInitUploadResponse(
        presigned_put_url=url,
        thumbnail_object_key=thumb_key,
        expires_in_seconds=settings.presigned_put_expires,
    )


async def thumbnail_complete(user: PluginUserContext, family_id: uuid.UUID, session) -> None:
    project_id = await _catalog_project_id(session)
    family = await repo.get_family(session, family_id)
    if not family:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Family not found")
    _ensure_family_access(user, family, project_id)
    thumb_key = _build_thumbnail_key(project_id, family.id)
    head = s3_service.head_object(thumb_key)
    family.has_thumbnail = head is not None
    await session.commit()
