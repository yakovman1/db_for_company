from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import FamilyLog


async def insert_log(session: AsyncSession, **kwargs: Any) -> FamilyLog:
    log = FamilyLog(**kwargs)
    session.add(log)
    await session.flush()
    return log


async def list_logs(
    session: AsyncSession,
    *,
    company_id: str | None = None,
    windows_user: str | None = None,
    family_id: uuid.UUID | None = None,
    action: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[FamilyLog]:
    q = select(FamilyLog).order_by(desc(FamilyLog.created_at))
    if company_id:
        q = q.where(FamilyLog.company_id == company_id)
    if windows_user:
        q = q.where(FamilyLog.windows_user == windows_user)
    if family_id:
        q = q.where(FamilyLog.family_id == family_id)
    if action:
        q = q.where(FamilyLog.action == action)
    q = q.limit(limit).offset(offset)
    result = await session.execute(q)
    return list(result.scalars().all())
