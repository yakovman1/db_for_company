from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import BimdataElement, BimdataSnapshot, BimdataSnapshotStatus
from app.schemas.auth import PluginUserContext
from app.schemas.bimdata import CreateSnapshotRequest, MepElementPayload


async def create_snapshot(
    session: AsyncSession,
    *,
    user: PluginUserContext,
    payload: CreateSnapshotRequest,
) -> BimdataSnapshot:
    snapshot_payload = payload.snapshot
    snapshot = BimdataSnapshot(
        company_id=user.company_id,
        created_by_windows_user=user.windows_user,
        schema_version=payload.schema_version,
        snapshot_date=snapshot_payload.snapshot_date,
        model_name=snapshot_payload.model_name,
        revit_version=snapshot_payload.revit_version,
        pbp_x=snapshot_payload.pbp_x,
        pbp_y=snapshot_payload.pbp_y,
        pbp_z=snapshot_payload.pbp_z,
        pbp_angle=snapshot_payload.pbp_angle,
        sp_x=snapshot_payload.sp_x,
        sp_y=snapshot_payload.sp_y,
        sp_z=snapshot_payload.sp_z,
        fop_name=snapshot_payload.fop_name,
        fop_path=snapshot_payload.fop_path,
        project_number=snapshot_payload.project_number,
        project_name=snapshot_payload.project_name,
        project_stage=snapshot_payload.project_stage,
        worksets_json=snapshot_payload.worksets_json,
        linked_files_json=snapshot_payload.linked_files_json,
        status=BimdataSnapshotStatus.CREATED,
    )
    session.add(snapshot)
    await session.flush()
    await session.commit()
    return snapshot


async def get_snapshot_for_company(
    session: AsyncSession,
    *,
    snapshot_id: uuid.UUID,
    company_id: str,
) -> BimdataSnapshot | None:
    stmt = select(BimdataSnapshot).where(
        BimdataSnapshot.id == snapshot_id,
        BimdataSnapshot.company_id == company_id,
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_snapshot_by_id(session: AsyncSession, *, snapshot_id: uuid.UUID) -> BimdataSnapshot | None:
    stmt = select(BimdataSnapshot).where(BimdataSnapshot.id == snapshot_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def upsert_elements(
    session: AsyncSession,
    *,
    snapshot_id: uuid.UUID,
    elements: Sequence[MepElementPayload],
) -> int:
    if not elements:
        return 0

    rows = [_element_to_row(snapshot_id, element) for element in elements]
    stmt = pg_insert(BimdataElement).values(rows)
    update_columns = {
        column.name: getattr(stmt.excluded, column.name)
        for column in BimdataElement.__table__.columns
        if column.name not in {"snapshot_id", "element_guid"}
    }
    stmt = stmt.on_conflict_do_update(
        index_elements=["snapshot_id", "element_guid"],
        set_=update_columns,
    )
    await session.execute(stmt)
    await session.commit()
    return len(rows)


async def mark_completed(session: AsyncSession, *, snapshot: BimdataSnapshot) -> BimdataSnapshot:
    snapshot.status = BimdataSnapshotStatus.COMPLETED
    snapshot.completed_at = datetime.now(timezone.utc)
    await session.flush()
    await session.commit()
    return snapshot


async def mark_failed(session: AsyncSession, *, snapshot: BimdataSnapshot) -> BimdataSnapshot:
    snapshot.status = BimdataSnapshotStatus.FAILED
    await session.flush()
    await session.commit()
    return snapshot


def _element_to_row(snapshot_id: uuid.UUID, element: MepElementPayload) -> dict:
    return {
        "snapshot_id": snapshot_id,
        "snapshot_date": element.snapshot_date,
        "element_guid": element.element_guid,
        "revit_id": element.revit_id,
        "category_name": element.category_name,
        "family_name": element.family_name,
        "type_name": element.type_name,
        "workset_name": element.workset_name,
        "level_guid": element.level_guid,
        "level_name": element.level_name,
        "space_guid": element.space_guid,
        "system_classification": element.system_classification,
        "system_name": element.system_name,
        "is_linear": element.is_linear,
        "length": element.length,
        "dimension_1": element.dimension_1,
        "dimension_2": element.dimension_2,
        "location_point": element.location_point.model_dump(mode="json") if element.location_point else None,
        "bounding_box_volume": element.bounding_box_volume,
        "bep_parameters": element.bep_parameters,
        "connectors_json": [connector.model_dump(mode="json") for connector in element.connectors_json],
    }

