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
)
from app.services import auth as auth_service
from app.services import families as family_service
from app.services import favorites as favorites_service

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


# ── Family card (опционально для клиента) — ПОСЛЕ всех специфичных ─────────────
@router.get("/{family_id}", response_model=FamilySummary)
async def get_family(
    family_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    user: PluginUserContext = Depends(auth_service.get_plugin_user),
) -> FamilySummary:
    family = await family_service.get_family(user, family_id, session)
    return FamilySummary.model_validate(family)
