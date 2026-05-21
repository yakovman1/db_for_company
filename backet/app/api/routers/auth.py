from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.schemas.auth import AuthRequest, AuthResponse
from app.services import auth as auth_service

router = APIRouter(tags=["auth"])


@router.post("/auth", response_model=AuthResponse)
async def login(
    payload: AuthRequest,
    session: AsyncSession = Depends(get_session),
) -> AuthResponse:
    return await auth_service.authenticate(payload, session)
