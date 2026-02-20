from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import UserProject


async def user_has_project(session: AsyncSession, user_id: uuid.UUID, project_id: uuid.UUID) -> bool:
    stmt = select(UserProject).where(UserProject.user_id == user_id, UserProject.project_id == project_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none() is not None


async def get_user_projects(session: AsyncSession, user_id: uuid.UUID) -> list[uuid.UUID]:
    stmt = select(UserProject.project_id).where(UserProject.user_id == user_id)
    result = await session.execute(stmt)
    return [row[0] for row in result.all()]

