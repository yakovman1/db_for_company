from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.schemas.auth import PluginUserContext
from app.schemas.family import FamilySummary, ListFamiliesResponse
from app.services import auth as auth_service
from app.services import families as family_service

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("/{project_id}/families", response_model=ListFamiliesResponse)
async def list_project_families(
    project_id: uuid.UUID,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    session: AsyncSession = Depends(get_session),
    user: PluginUserContext = Depends(auth_service.get_plugin_user),
) -> ListFamiliesResponse:
    # Rev 7: legacy route разрешён только для shared_catalog_project_id
    company_project_id = await auth_service.resolve_shared_catalog_project_id(session)
    if project_id != company_project_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Project access denied")

    families, total = await family_service.list_families(user, limit, offset, session)
    items = [FamilySummary.model_validate(f) for f in families]
    return ListFamiliesResponse(items=items, total=total)
