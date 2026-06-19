from __future__ import annotations

import uuid

from fastapi import Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import BimdataSnapshot, BimdataSnapshotStatus
from app.db.repositories import bimdata as bimdata_repo
from app.schemas.auth import PluginUserContext
from app.schemas.bimdata import (
    BatchResponse,
    CompleteSnapshotRequest,
    CreateSnapshotRequest,
    ElementsBatchRequest,
    FailSnapshotRequest,
    SnapshotStatusResponse,
    SUPPORTED_SCHEMA_VERSION,
)


class BimdataError(Exception):
    def __init__(self, status_code: int, error_code: str, message: str) -> None:
        self.status_code = status_code
        self.error_code = error_code
        self.message = message


async def bimdata_error_handler(_: Request, exc: BimdataError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"errorCode": exc.error_code, "message": exc.message},
    )


async def create_snapshot(
    user: PluginUserContext,
    payload: CreateSnapshotRequest,
    session: AsyncSession,
) -> SnapshotStatusResponse:
    _validate_schema_version(payload.schema_version)
    _validate_source_matches_user(user, payload)

    snapshot = await bimdata_repo.create_snapshot(session, user=user, payload=payload)
    return _snapshot_response(snapshot)


async def upload_elements_batch(
    user: PluginUserContext,
    snapshot_id: uuid.UUID,
    payload: ElementsBatchRequest,
    session: AsyncSession,
) -> BatchResponse:
    _validate_schema_version(payload.schema_version)
    snapshot = await _get_owned_snapshot(session, user=user, snapshot_id=snapshot_id)
    _ensure_snapshot_accepts_batches(snapshot)

    accepted = await bimdata_repo.upsert_elements(session, snapshot_id=snapshot.id, elements=payload.elements)
    return BatchResponse(accepted=accepted, rejected=0, errors=[])


async def complete_snapshot(
    user: PluginUserContext,
    snapshot_id: uuid.UUID,
    payload: CompleteSnapshotRequest,
    session: AsyncSession,
) -> SnapshotStatusResponse:
    _ = payload
    snapshot = await _get_owned_snapshot(session, user=user, snapshot_id=snapshot_id)
    _ensure_snapshot_not_terminal(snapshot)

    completed = await bimdata_repo.mark_completed(session, snapshot=snapshot)
    return _snapshot_response(completed)


async def fail_snapshot(
    user: PluginUserContext,
    snapshot_id: uuid.UUID,
    payload: FailSnapshotRequest,
    session: AsyncSession,
) -> SnapshotStatusResponse:
    _ = payload
    snapshot = await _get_owned_snapshot(session, user=user, snapshot_id=snapshot_id)

    failed = await bimdata_repo.mark_failed(session, snapshot=snapshot)
    return _snapshot_response(failed)


def _validate_schema_version(schema_version: str) -> None:
    if schema_version != SUPPORTED_SCHEMA_VERSION:
        raise BimdataError(
            status.HTTP_400_BAD_REQUEST,
            "UNSUPPORTED_SCHEMA_VERSION",
            f"Unsupported schemaVersion '{schema_version}'. Expected '{SUPPORTED_SCHEMA_VERSION}'.",
        )


def _validate_source_matches_user(user: PluginUserContext, payload: CreateSnapshotRequest) -> None:
    if payload.source.company_id != user.company_id or payload.source.windows_user != user.windows_user:
        raise BimdataError(
            status.HTTP_403_FORBIDDEN,
            "SOURCE_TOKEN_MISMATCH",
            "Snapshot source does not match authenticated token context.",
        )


async def _get_owned_snapshot(
    session: AsyncSession,
    *,
    user: PluginUserContext,
    snapshot_id: uuid.UUID,
) -> BimdataSnapshot:
    snapshot = await bimdata_repo.get_snapshot_by_id(session, snapshot_id=snapshot_id)
    if snapshot is None:
        raise BimdataError(status.HTTP_404_NOT_FOUND, "SNAPSHOT_NOT_FOUND", "Snapshot not found.")
    if snapshot.company_id != user.company_id:
        raise BimdataError(
            status.HTTP_403_FORBIDDEN,
            "SNAPSHOT_FORBIDDEN",
            "Authenticated user is not allowed to access this snapshot.",
        )
    return snapshot


def _ensure_snapshot_accepts_batches(snapshot: BimdataSnapshot) -> None:
    if snapshot.status in {BimdataSnapshotStatus.COMPLETED, BimdataSnapshotStatus.FAILED}:
        raise BimdataError(
            status.HTTP_409_CONFLICT,
            "SNAPSHOT_CLOSED",
            "Snapshot is already completed or failed.",
        )


def _ensure_snapshot_not_terminal(snapshot: BimdataSnapshot) -> None:
    if snapshot.status in {BimdataSnapshotStatus.COMPLETED, BimdataSnapshotStatus.FAILED}:
        raise BimdataError(
            status.HTTP_409_CONFLICT,
            "SNAPSHOT_CLOSED",
            "Snapshot is already completed or failed.",
        )


def _snapshot_response(snapshot: BimdataSnapshot) -> SnapshotStatusResponse:
    status_value = snapshot.status.value if isinstance(snapshot.status, BimdataSnapshotStatus) else str(snapshot.status)
    return SnapshotStatusResponse(snapshot_id=snapshot.id, status=status_value)

