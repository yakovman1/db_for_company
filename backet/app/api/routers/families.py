from __future__ import annotations

import uuid
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.schemas.auth import PluginUserContext
from app.schemas.family import (
    AddFavoriteRequest,
    CompleteUploadRequest,
    DownloadUrlResponse,
    FavoriteItem,
    FavoritesListResponse,
    FamilySummary,
    InitUploadRequest,
    InitUploadResponse,
    ListFamiliesResponse,
    MetadataRequest,
    ThumbnailInitUploadResponse,
)
from app.schemas.familylogs import FamilyLogEntry, GetLogsResponse, PostLogsRequest
from app.services import auth as auth_service
from app.services import families as family_service
from app.services import favorites as favorites_service
from app.services import familylogs as log_service
import app.db.repositories as repo

router = APIRouter(prefix="/families", tags=["families"])


# ── List ──────────────────────────────────────────────────────────────────────
@router.get("", response_model=ListFamiliesResponse)
async def list_company_families(
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    is_primary: Annotated[Optional[bool], Query(alias="is_primary")] = None,
    parent_id: Annotated[Optional[uuid.UUID], Query(alias="parent_id")] = None,
    session: AsyncSession = Depends(get_session),
    user: PluginUserContext = Depends(auth_service.get_plugin_user),
) -> ListFamiliesResponse:
    families, total = await family_service.list_families(
        user, limit, offset, session, is_primary=is_primary, parent_id=parent_id
    )
    items = [FamilySummary.model_validate(f) for f in families]
    return ListFamiliesResponse(items=items, total=total)


# ── Init upload ───────────────────────────────────────────────────────────────
@router.post("/init-upload", response_model=InitUploadResponse)
async def init_upload(
    payload: InitUploadRequest,
    session: AsyncSession = Depends(get_session),
    user: PluginUserContext = Depends(auth_service.get_plugin_user),
) -> InitUploadResponse:
    return await family_service.init_upload(user, payload, session)


# ── Favorites — ПЕРЕД /{family_id} ────────────────────────────────────────────
@router.get("/favorites", response_model=FavoritesListResponse)
async def list_favorites(
    session: AsyncSession = Depends(get_session),
    user: PluginUserContext = Depends(auth_service.get_plugin_user),
) -> FavoritesListResponse:
    return await favorites_service.list_favorites(user, session)


@router.post("/favorites", response_model=FavoriteItem, status_code=status.HTTP_200_OK)
async def add_favorite(
    payload: AddFavoriteRequest,
    session: AsyncSession = Depends(get_session),
    user: PluginUserContext = Depends(auth_service.get_plugin_user),
) -> FavoriteItem:
    return await favorites_service.add_favorite(user, payload, session)


@router.delete("/favorites/{family_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_favorite(
    family_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    user: PluginUserContext = Depends(auth_service.get_plugin_user),
) -> Response:
    await favorites_service.remove_favorite(user, family_id, session)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ── Metadata / Complete ───────────────────────────────────────────────────────
@router.post("/{family_id}/metadata", response_model=dict)
async def save_metadata(
    family_id: uuid.UUID,
    payload: MetadataRequest,
    session: AsyncSession = Depends(get_session),
    user: PluginUserContext = Depends(auth_service.get_plugin_user),
) -> dict:
    await family_service.save_metadata(user, family_id, payload.metadata, session)
    return {"ok": True}


@router.post("/{family_id}/complete", response_model=dict)
async def complete_upload(
    family_id: uuid.UUID,
    payload: CompleteUploadRequest,
    session: AsyncSession = Depends(get_session),
    user: PluginUserContext = Depends(auth_service.get_plugin_user),
) -> dict:
    await family_service.complete_upload(user, family_id, payload, session)
    return {"ok": True}


# ── Download URL ──────────────────────────────────────────────────────────────
@router.get("/{family_id}/download-url", response_model=DownloadUrlResponse)
async def get_download_url(
    family_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    user: PluginUserContext = Depends(auth_service.get_plugin_user),
) -> DownloadUrlResponse:
    url = await family_service.get_download_url(user, family_id, session)
    return DownloadUrlResponse(
        presigned_get_url=url, expires_in_seconds=family_service.settings.presigned_get_expires
    )


# ── Thumbnail URL ─────────────────────────────────────────────────────────────
@router.get("/{family_id}/thumbnail-url", response_model=DownloadUrlResponse)
async def get_thumbnail_url(
    family_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    user: PluginUserContext = Depends(auth_service.get_plugin_user),
) -> DownloadUrlResponse:
    url = await family_service.get_thumbnail_url(user, family_id, session)
    return DownloadUrlResponse(
        presigned_get_url=url, expires_in_seconds=family_service.settings.presigned_get_expires
    )


# ── Thumbnail upload (rev 5.1) ────────────────────────────────────────────────
@router.post("/{family_id}/thumbnail/init-upload", response_model=ThumbnailInitUploadResponse)
async def thumbnail_init_upload(
    family_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    user: PluginUserContext = Depends(auth_service.get_plugin_user),
) -> ThumbnailInitUploadResponse:
    return await family_service.thumbnail_init_upload(user, family_id, session)


@router.post("/{family_id}/thumbnail/complete", response_model=dict)
async def thumbnail_complete(
    family_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    user: PluginUserContext = Depends(auth_service.get_plugin_user),
) -> dict:
    await family_service.thumbnail_complete(user, family_id, session)
    return {"ok": True}


# ── Logs (rev 8) — ПЕРЕД /{family_id} ────────────────────────────────────────
@router.post("/logs", status_code=status.HTTP_200_OK, response_model=dict)
async def post_logs(
    payload: PostLogsRequest,
    session: AsyncSession = Depends(get_session),
    user: PluginUserContext = Depends(auth_service.get_plugin_user),
) -> dict:
    """Приём клиентских событий (download_file, load_into_project, ошибки и т.п.)."""
    for entry in payload.entries:
        await log_service.log(
            session,
            action=entry.action,
            outcome=entry.outcome,
            source="client",
            company_id=user.company_id,
            windows_user=user.windows_user,
            family_id=entry.family_id,
            family_name=entry.family_name,
            original_filename=entry.original_filename,
            category=entry.category,
            family_version=entry.family_version,
            is_primary=entry.is_primary,
            parent_family_id=entry.parent_family_id,
            revit_project_name=entry.revit_project_name,
            revit_project_path=entry.revit_project_path,
            revit_document_kind=entry.revit_document_kind,
            error_message=entry.error_message,
            http_status=entry.http_status,
            details=entry.details,
        )
    return {"ok": True, "accepted": len(payload.entries)}


@router.get("/logs", response_model=GetLogsResponse)
async def get_logs(
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    family_id: Annotated[Optional[uuid.UUID], Query()] = None,
    action: Annotated[Optional[str], Query()] = None,
    session: AsyncSession = Depends(get_session),
    user: PluginUserContext = Depends(auth_service.get_plugin_user),
) -> GetLogsResponse:
    """Просмотр журнала — фильтр по текущему пользователю (company_id + windows_user из JWT)."""
    rows = await repo.list_logs(
        session,
        company_id=user.company_id,
        windows_user=user.windows_user,
        family_id=family_id,
        action=action,
        limit=limit,
        offset=offset,
    )
    return GetLogsResponse(items=[FamilyLogEntry.model_validate(r) for r in rows])


# ── Family card (опционально для клиента) — ПОСЛЕ всех специфичных ─────────────
@router.get("/{family_id}", response_model=FamilySummary)
async def get_family(
    family_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    user: PluginUserContext = Depends(auth_service.get_plugin_user),
) -> FamilySummary:
    family = await family_service.get_family(user, family_id, session)
    return FamilySummary.model_validate(family)
