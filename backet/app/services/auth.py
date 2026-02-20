from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.repositories.user_projects import get_user_projects
from app.db.session import get_session
from app.schemas.auth import UserContext

logger = get_logger(__name__)
settings = get_settings()


async def get_current_user(
    authorization: Annotated[str | None, Header(alias="Authorization")],
    session: AsyncSession = Depends(get_session),
) -> UserContext:
    if not authorization:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Authorization header")

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Authorization header")

    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        sub = payload.get("sub")
        if not sub:
            raise ValueError("Missing sub")
        user_id = uuid.UUID(str(sub))
    except (JWTError, ValueError) as exc:
        logger.warning("jwt_decode_failed", error=str(exc))
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc

    project_ids = await get_user_projects(session, user_id=user_id)
    return UserContext(user_id=user_id, project_ids=project_ids)

