from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.schemas.auth import AuthResponse, FamilyAuthRequest
from app.services import auth as auth_service

router = APIRouter(tags=["family-auth"])


@router.post("/family/auth", response_model=AuthResponse)
async def family_login(
    payload: FamilyAuthRequest,
    session: AsyncSession = Depends(get_session),
) -> AuthResponse:
    """Rev 9: вход в FamilyMang без Company ID — только windowsUser."""
    return await auth_service.authenticate_family_user(payload, session)
