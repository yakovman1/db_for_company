from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.schemas.auth import PluginUserContext
from app.schemas.opening import OpeningsListResponse, SyncOpeningsRequest, SyncOpeningsResponse
from app.services import auth as auth_service
from app.services import openings as openings_service

router = APIRouter(prefix="/openings", tags=["openings"])


@router.post("/sync", response_model=SyncOpeningsResponse)
async def sync_openings(
    payload: SyncOpeningsRequest,
    session: AsyncSession = Depends(get_session),
    user: PluginUserContext = Depends(auth_service.get_plugin_user),
) -> SyncOpeningsResponse:
    return await openings_service.sync_openings(user, payload, session)


@router.get("", response_model=OpeningsListResponse)
async def get_openings(
    model_guid: Annotated[uuid.UUID, Query(alias="modelGuid")],
    session: AsyncSession = Depends(get_session),
    user: PluginUserContext = Depends(auth_service.get_plugin_user),
) -> OpeningsListResponse:
    return await openings_service.list_openings(user, model_guid, session)
