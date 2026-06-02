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
from app.schemas.auth import AuthRequest, AuthResponse, PluginUserContext, UserContext
from app.services import familylogs as log_service

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
        await log_service.log(
            session, action="auth_login_failed", outcome="error",
            company_id=payload.company_id, windows_user=payload.windows_user,
            http_status=401, error_message="Company not found or inactive",
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Company not found or inactive")

    # Rev 7: всегда проверяем company_users (убрана проверка "if count > 0")
    allowed = await companies_repo.is_windows_user_allowed(
        session,
        company_id=payload.company_id,
        windows_user=payload.windows_user,
    )
    if not allowed:
        await log_service.log(
            session, action="auth_login_failed", outcome="error",
            company_id=payload.company_id, windows_user=payload.windows_user,
            http_status=403, error_message="Windows user is not allowed",
        )
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Windows user is not allowed")

    result = _create_plugin_token(payload.company_id, payload.windows_user)
    await log_service.log(
        session, action="auth_login", outcome="success",
        company_id=payload.company_id, windows_user=payload.windows_user,
    )
    return result


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
