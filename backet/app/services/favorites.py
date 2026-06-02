from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

import app.db.repositories as repo
from app.schemas.auth import FamilyPluginUserContext
from app.schemas.family import AddFavoriteRequest, FavoriteItem, FavoritesListResponse
from app.services import auth as auth_service


async def list_favorites(user: FamilyPluginUserContext, session: AsyncSession) -> FavoritesListResponse:
    rows = await repo.list_favorites(session, company_id=user.company_id, windows_user=user.windows_user)
    items = [FavoriteItem.model_validate(r) for r in rows]
    return FavoritesListResponse(items=items)


async def add_favorite(
    user: FamilyPluginUserContext, payload: AddFavoriteRequest, session: AsyncSession
) -> FavoriteItem:
    # Rev 7: проверяем принадлежность семейства к единому каталогу
    project_id = await auth_service.resolve_shared_catalog_project_id(session)
    family = await repo.get_family(session, payload.family_id)
    if not family or family.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Family not found")

    fav = await repo.add_favorite(
        session,
        company_id=user.company_id,
        windows_user=user.windows_user,
        family_id=payload.family_id,
    )
    return FavoriteItem.model_validate(fav)


async def remove_favorite(user: FamilyPluginUserContext, family_id: uuid.UUID, session: AsyncSession) -> None:
    await repo.remove_favorite(
        session,
        company_id=user.company_id,
        windows_user=user.windows_user,
        family_id=family_id,
    )
