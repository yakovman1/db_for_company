from __future__ import annotations

import uuid
from datetime import datetime
from typing import Iterable, Optional, Sequence

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
    family_name: str | None = None,
    category: str | None = None,
    is_primary: bool | None = None,
    parent_family_id: uuid.UUID | None = None,
    version: int = 1,
) -> Family:
    family = Family(
        id=family_id or uuid.uuid4(),
        project_id=project_id,
        bucket=bucket,
        object_key=object_key,
        original_filename=original_filename,
        sha256=sha256,
        size_bytes=size_bytes,
        family_name=family_name,
        category=category,
        is_primary=is_primary,
        parent_family_id=parent_family_id,
        version=version,
        status=FamilyStatus.INITIATED,
    )
    session.add(family)
    await session.commit()
    await session.refresh(family)
    return family


async def find_family_by_identity(
    session: AsyncSession,
    *,
    project_id: uuid.UUID,
    family_name: str,
    category: str,
    is_primary: bool,
    parent_family_id: uuid.UUID | None,
) -> Family | None:
    stmt = select(Family).where(
        Family.project_id == project_id,
        Family.family_name == family_name,
        Family.category == category,
        Family.is_primary == is_primary,
    )
    if parent_family_id is not None:
        stmt = stmt.where(Family.parent_family_id == parent_family_id)
    else:
        stmt = stmt.where(Family.parent_family_id.is_(None))
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def increment_version(
    session: AsyncSession,
    *,
    family: Family,
    sha256: str | None,
    size_bytes: int | None,
    original_filename: str,
    object_key: str,
) -> Family:
    family.version = family.version + 1
    family.sha256 = sha256
    family.size_bytes = size_bytes
    family.original_filename = original_filename
    family.object_key = object_key
    family.status = FamilyStatus.INITIATED
    await session.commit()
    await session.refresh(family)
    return family


async def get_family(session: AsyncSession, family_id: uuid.UUID) -> Family | None:
    stmt = select(Family).where(Family.id == family_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def list_families_by_project(
    session: AsyncSession,
    *,
    project_id: uuid.UUID,
    limit: int = 20,
    offset: int = 0,
    is_primary: Optional[bool] = None,
    parent_id: Optional[uuid.UUID] = None,
) -> Sequence[Family]:
    stmt = (
        select(Family)
        .where(Family.project_id == project_id)
    )
    if is_primary is not None:
        val = "true" if is_primary else "false"
        stmt = stmt.where(Family.metadata_json["extra"]["is_primary"].astext == val)
    if parent_id is not None:
        stmt = stmt.where(Family.metadata_json["extra"]["parent_family_id"].astext == str(parent_id))
    stmt = stmt.order_by(Family.created_at.desc()).limit(limit).offset(offset)
    result = await session.execute(stmt)
    return result.scalars().all()


async def count_families_by_project(
    session: AsyncSession,
    *,
    project_id: uuid.UUID,
    is_primary: Optional[bool] = None,
    parent_id: Optional[uuid.UUID] = None,
) -> int:
    stmt = select(func.count()).select_from(Family).where(Family.project_id == project_id)
    if is_primary is not None:
        val = "true" if is_primary else "false"
        stmt = stmt.where(Family.metadata_json["extra"]["is_primary"].astext == val)
    if parent_id is not None:
        stmt = stmt.where(Family.metadata_json["extra"]["parent_family_id"].astext == str(parent_id))
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

