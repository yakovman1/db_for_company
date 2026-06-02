from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.repositories import companies as companies_repo
from app.db.repositories.user_projects import get_user_projects
from app.db.session import get_session
from app.schemas.auth import (
    AuthRequest,
    AuthResponse,
    FamilyAuthRequest,
    FamilyPluginUserContext,
    PluginUserContext,
    UserContext,
)

logger = get_logger(__name__)
settings = get_settings()


def _decode_bearer_token(authorization: str | None) -> dict:
    if not authorization:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Authorization header")

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Authorization header")

    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        logger.warning("jwt_decode_failed", error=str(exc))
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc


def _create_plugin_token(company_id: str, windows_user: str) -> AuthResponse:
    expires_in = settings.jwt_expires_seconds
    payload = {
        "company_id": company_id,
        "windows_user": windows_user,
        "exp": datetime.now(timezone.utc) + timedelta(seconds=expires_in),
    }
    access_token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return AuthResponse(access_token=access_token, expires_in=expires_in)


async def authenticate(payload: AuthRequest, session: AsyncSession) -> AuthResponse:
    company = await companies_repo.get_company(session, company_id=payload.company_id)
    if company is None or not company.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Company not found or inactive")

    # Rev 7: всегда проверяем company_users (убрана проверка "if count > 0")
    allowed = await companies_repo.is_windows_user_allowed(
        session,
        company_id=payload.company_id,
        windows_user=payload.windows_user,
    )
    if not allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Windows user is not allowed")

    return _create_plugin_token(payload.company_id, payload.windows_user)


async def get_current_user(
    authorization: Annotated[str | None, Header(alias="Authorization")],
    session: AsyncSession = Depends(get_session),
) -> UserContext:
    payload = _decode_bearer_token(authorization)

    try:
        sub = payload.get("sub")
        if not sub:
            raise ValueError("Missing sub")
        user_id = uuid.UUID(str(sub))
    except ValueError as exc:
        logger.warning("jwt_decode_failed", error=str(exc))
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc

    project_ids = await get_user_projects(session, user_id=user_id)
    return UserContext(user_id=user_id, project_ids=project_ids)


async def resolve_company_project_id(session: AsyncSession, company_id: str) -> uuid.UUID:
    """Устаревшее: использовать resolve_shared_catalog_project_id()."""
    company = await companies_repo.get_company(session, company_id=company_id)
    if company is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Company not found")
    return company.id


async def resolve_shared_catalog_project_id(session: AsyncSession) -> uuid.UUID:
    """Rev 7: единый каталог — возвращает UUID компании-носителя SHARED_CATALOG_COMPANY_ID."""
    catalog_id = settings.shared_catalog_company_id
    company = await companies_repo.get_company(session, company_id=catalog_id)
    if company is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Shared catalog company '{catalog_id}' not found in database",
        )
    return company.id


async def get_plugin_user(
    authorization: Annotated[str | None, Header(alias="Authorization")],
    session: AsyncSession = Depends(get_session),
) -> PluginUserContext:
    payload = _decode_bearer_token(authorization)

    company_id = payload.get("company_id")
    windows_user = payload.get("windows_user")
    if not company_id or not windows_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    company = await companies_repo.get_company(session, company_id=str(company_id))
    if company is None or not company.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Company not found or inactive")

    # Rev 7: всегда проверяем company_users
    allowed = await companies_repo.is_windows_user_allowed(
        session,
        company_id=str(company_id),
        windows_user=str(windows_user),
    )
    if not allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Windows user is not allowed")

    return PluginUserContext(company_id=str(company_id), windows_user=str(windows_user))


# ── Rev 9: FamilyMang user-only auth ──────────────────────────────────────────

def _create_family_token(windows_user: str) -> AuthResponse:
    """JWT только с windows_user — без company_id."""
    expires_in = settings.jwt_expires_seconds
    payload = {
        "windows_user": windows_user,
        "exp": datetime.now(timezone.utc) + timedelta(seconds=expires_in),
    }
    access_token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return AuthResponse(access_token=access_token, expires_in=expires_in)


async def authenticate_family_user(payload: FamilyAuthRequest, session: AsyncSession) -> AuthResponse:
    """Rev 9: вход без Company ID — только windows_user в whitelist."""
    allowed = await companies_repo.is_windows_user_in_whitelist(
        session, windows_user=payload.windows_user
    )
    if not allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Windows user is not allowed")
    return _create_family_token(payload.windows_user)


async def get_family_plugin_user(
    authorization: Annotated[str | None, Header(alias="Authorization")],
    session: AsyncSession = Depends(get_session),
) -> FamilyPluginUserContext:
    """Rev 9: dependency для /families/* — принимает FamilyMang JWT (без company_id)."""
    token_payload = _decode_bearer_token(authorization)

    windows_user = token_payload.get("windows_user")
    if not windows_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    allowed = await companies_repo.is_windows_user_in_whitelist(
        session, windows_user=str(windows_user)
    )
    if not allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Windows user is not allowed")

    return FamilyPluginUserContext(windows_user=str(windows_user))
