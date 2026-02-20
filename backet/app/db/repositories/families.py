from __future__ import annotations

import uuid
from datetime import datetime
from typing import Iterable, Sequence

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Family, FamilyParameter, FamilyStatus, FamilyTypeValue


async def create_family(
    session: AsyncSession,
    *,
    family_id: uuid.UUID | None = None,
    project_id: uuid.UUID,
    bucket: str,
    object_key: str,
    original_filename: str,
    sha256: str | None,
    size_bytes: int | None,
) -> Family:
    family = Family(
        id=family_id or uuid.uuid4(),
        project_id=project_id,
        bucket=bucket,
        object_key=object_key,
        original_filename=original_filename,
        sha256=sha256,
        size_bytes=size_bytes,
        status=FamilyStatus.INITIATED,
    )
    session.add(family)
    await session.commit()
    await session.refresh(family)
    return family


async def get_family(session: AsyncSession, family_id: uuid.UUID) -> Family | None:
    stmt = select(Family).where(Family.id == family_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def list_families_by_project(
    session: AsyncSession, *, project_id: uuid.UUID, limit: int = 50, offset: int = 0
) -> Sequence[Family]:
    stmt = (
        select(Family)
        .where(Family.project_id == project_id)
        .order_by(Family.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    result = await session.execute(stmt)
    return result.scalars().all()


async def count_families_by_project(session: AsyncSession, *, project_id: uuid.UUID) -> int:
    stmt = select(func.count()).select_from(Family).where(Family.project_id == project_id)
    result = await session.execute(stmt)
    return int(result.scalar_one())


async def update_metadata(
    session: AsyncSession,
    *,
    family: Family,
    metadata_json: dict,
    parameters: Iterable[dict] | None = None,
    type_values: Iterable[dict] | None = None,
) -> Family:
    family.metadata_json = metadata_json
    family.status = FamilyStatus.PARSED

    if parameters is not None:
        await session.execute(delete(FamilyParameter).where(FamilyParameter.family_id == family.id))
        session.add_all([FamilyParameter(family_id=family.id, **param) for param in parameters])

    if type_values is not None:
        await session.execute(delete(FamilyTypeValue).where(FamilyTypeValue.family_id == family.id))
        session.add_all([FamilyTypeValue(family_id=family.id, **tv) for tv in type_values])

    await session.commit()
    await session.refresh(family)
    return family


async def mark_ready(
    session: AsyncSession,
    *,
    family: Family,
    etag: str | None = None,
    uploaded_at: datetime | None = None,
    size_bytes: int | None = None,
    status: FamilyStatus = FamilyStatus.READY,
) -> Family:
    family.status = status
    if etag:
        family.etag = etag
    if uploaded_at:
        family.uploaded_at = uploaded_at
    if size_bytes:
        family.size_bytes = size_bytes
    await session.commit()
    await session.refresh(family)
    return family


async def update_status(session: AsyncSession, *, family: Family, status: FamilyStatus) -> Family:
    family.status = status
    await session.commit()
    await session.refresh(family)
    return family


async def update_object_key(
    session: AsyncSession, *, family_id: uuid.UUID, object_key: str, bucket: str
) -> None:
    stmt = (
        update(Family)
        .where(Family.id == family_id)
        .values(object_key=object_key, bucket=bucket)
        .execution_options(synchronize_session="fetch")
    )
    await session.execute(stmt)
    await session.commit()

