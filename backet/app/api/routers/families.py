from __future__ import annotations

import uuid
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.schemas.auth import PluginUserContext
from app.schemas.family import (
    CompleteUploadRequest,
    DownloadUrlResponse,
    FamilySummary,
    InitUploadRequest,
    InitUploadResponse,
    ListFamiliesResponse,
    MetadataRequest,
)
from app.services import auth as auth_service
from app.services import families as family_service

router = APIRouter(prefix="/families", tags=["families"])


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


@router.post("/init-upload", response_model=InitUploadResponse)
async def init_upload(
    payload: InitUploadRequest,
    session: AsyncSession = Depends(get_session),
    user: PluginUserContext = Depends(auth_service.get_plugin_user),
) -> InitUploadResponse:
    return await family_service.init_upload(user, payload, session)


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


@router.get("/{family_id}", response_model=FamilySummary)
async def get_family(
    family_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    user: PluginUserContext = Depends(auth_service.get_plugin_user),
) -> FamilySummary:
    family = await family_service.get_family(user, family_id, session)
    return FamilySummary.model_validate(family)
