from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Path
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.schemas.auth import PluginUserContext
from app.schemas.bimdata import (
    BatchResponse,
    CompleteSnapshotRequest,
    CreateSnapshotRequest,
    ElementsBatchRequest,
    FailSnapshotRequest,
    SnapshotStatusResponse,
)
from app.services import auth as auth_service
from app.services import bimdata as bimdata_service

router = APIRouter(prefix="/bimdata", tags=["bimdata"])


@router.post("/snapshots", response_model=SnapshotStatusResponse)
async def create_snapshot(
    payload: CreateSnapshotRequest,
    session: AsyncSession = Depends(get_session),
    user: PluginUserContext = Depends(auth_service.get_plugin_user),
) -> SnapshotStatusResponse:
    return await bimdata_service.create_snapshot(user, payload, session)


@router.post("/snapshots/{snapshotId}/elements:batch", response_model=BatchResponse)
async def upload_elements_batch(
    payload: ElementsBatchRequest,
    snapshot_id: uuid.UUID = Path(alias="snapshotId"),
    session: AsyncSession = Depends(get_session),
    user: PluginUserContext = Depends(auth_service.get_plugin_user),
) -> BatchResponse:
    return await bimdata_service.upload_elements_batch(user, snapshot_id, payload, session)


@router.post("/snapshots/{snapshotId}:complete", response_model=SnapshotStatusResponse)
async def complete_snapshot(
    payload: CompleteSnapshotRequest,
    snapshot_id: uuid.UUID = Path(alias="snapshotId"),
    session: AsyncSession = Depends(get_session),
    user: PluginUserContext = Depends(auth_service.get_plugin_user),
) -> SnapshotStatusResponse:
    return await bimdata_service.complete_snapshot(user, snapshot_id, payload, session)


@router.post("/snapshots/{snapshotId}:fail", response_model=SnapshotStatusResponse)
async def fail_snapshot(
    payload: FailSnapshotRequest,
    snapshot_id: uuid.UUID = Path(alias="snapshotId"),
    session: AsyncSession = Depends(get_session),
    user: PluginUserContext = Depends(auth_service.get_plugin_user),
) -> SnapshotStatusResponse:
    return await bimdata_service.fail_snapshot(user, snapshot_id, payload, session)

