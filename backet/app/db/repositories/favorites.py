from __future__ import annotations

import uuid
from datetime import datetime
from typing import Sequence

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import UserFavorite


async def list_favorites(
    session: AsyncSession,
    *,
    company_id: str,
    windows_user: str,
) -> Sequence[UserFavorite]:
    stmt = (
        select(UserFavorite)
        .where(UserFavorite.company_id == company_id, UserFavorite.windows_user == windows_user)
        .order_by(UserFavorite.created_at.desc())
    )
    result = await session.execute(stmt)
    return result.scalars().all()


async def add_favorite(
    session: AsyncSession,
    *,
    company_id: str,
    windows_user: str,
    family_id: uuid.UUID,
) -> UserFavorite:
    existing = await session.get(UserFavorite, (company_id, windows_user, family_id))
    if existing:
        return existing
    fav = UserFavorite(company_id=company_id, windows_user=windows_user, family_id=family_id)
    session.add(fav)
    await session.commit()
    await session.refresh(fav)
    return fav


async def remove_favorite(
    session: AsyncSession,
    *,
    company_id: str,
    windows_user: str,
    family_id: uuid.UUID,
) -> None:
    stmt = delete(UserFavorite).where(
        UserFavorite.company_id == company_id,
        UserFavorite.windows_user == windows_user,
        UserFavorite.family_id == family_id,
    )
    await session.execute(stmt)
    await session.commit()
