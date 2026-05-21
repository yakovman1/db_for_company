from __future__ import annotations

import uuid
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Opening, OpeningHistory, OpeningHistoryEventType, OpeningStatus


async def list_openings_by_model(session: AsyncSession, *, model_guid: uuid.UUID) -> Sequence[Opening]:
    stmt = select(Opening).where(Opening.model_guid == model_guid).order_by(Opening.id)
    result = await session.execute(stmt)
    return result.scalars().all()


async def add_opening_history(
    session: AsyncSession,
    *,
    opening_id: int,
    event_type: OpeningHistoryEventType,
    payload: dict | None = None,
    created_by: str | None = None,
) -> None:
    session.add(
        OpeningHistory(
            opening_id=opening_id,
            event_type=event_type,
            payload=payload,
            created_by=created_by,
        )
    )
