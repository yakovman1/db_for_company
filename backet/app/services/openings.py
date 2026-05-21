from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.models import Opening, OpeningHistoryEventType, OpeningStatus
from app.db.repositories import openings as openings_repo
from app.schemas.auth import PluginUserContext
from app.schemas.opening import (
    OpeningItemPayload,
    OpeningStatusItem,
    OpeningsListResponse,
    SyncOpeningItemResult,
    SyncOpeningsRequest,
    SyncOpeningsResponse,
)

logger = get_logger(__name__)

STATUS_PARAM = "ATP_OPN_Статус отверстия"


def _sync_extra_fields(extra_fields: dict[str, Any] | None) -> dict[str, Any]:
    if not extra_fields:
        return {}
    return {key: value for key, value in extra_fields.items() if key != STATUS_PARAM}


def _payload_snapshot(opening: OpeningItemPayload, schedule_name: str) -> dict[str, Any]:
    return {
        "element_id": opening.element_id,
        "family_name": opening.family_name,
        "type_name": opening.type_name,
        "category_name": opening.category_name,
        "level_name": opening.level_name,
        "location_x": opening.location.x,
        "location_y": opening.location.y,
        "location_z": opening.location.z,
        "width": opening.dimensions.width,
        "height": opening.dimensions.height,
        "depth": opening.dimensions.depth,
        "diameter": opening.dimensions.diameter,
        "extra_fields": _sync_extra_fields(opening.extra_fields),
        "schedule_name": schedule_name,
    }


def _opening_snapshot(opening: Opening) -> dict[str, Any]:
    return {
        "element_id": opening.element_id,
        "family_name": opening.family_name,
        "type_name": opening.type_name,
        "category_name": opening.category_name,
        "level_name": opening.level_name,
        "location_x": opening.location_x,
        "location_y": opening.location_y,
        "location_z": opening.location_z,
        "width": opening.width,
        "height": opening.height,
        "depth": opening.depth,
        "diameter": opening.diameter,
        "extra_fields": _sync_extra_fields(opening.extra_fields),
        "schedule_name": opening.schedule_name,
    }


def _apply_payload(opening: Opening, payload: OpeningItemPayload, schedule_name: str) -> None:
    opening.element_id = payload.element_id
    opening.family_name = payload.family_name
    opening.type_name = payload.type_name
    opening.category_name = payload.category_name
    opening.level_name = payload.level_name
    opening.location_x = payload.location.x
    opening.location_y = payload.location.y
    opening.location_z = payload.location.z
    opening.width = payload.dimensions.width
    opening.height = payload.dimensions.height
    opening.depth = payload.dimensions.depth
    opening.diameter = payload.dimensions.diameter
    opening.extra_fields = _sync_extra_fields(payload.extra_fields)
    opening.schedule_name = schedule_name


def _create_opening(model_guid: uuid.UUID, payload: OpeningItemPayload, schedule_name: str) -> Opening:
    opening = Opening(
        model_guid=model_guid,
        element_unique_id=payload.element_unique_id,
        status=OpeningStatus.NEW,
    )
    _apply_payload(opening, payload, schedule_name)
    return opening


def _history_actor(user: PluginUserContext) -> str:
    return f"{user.company_id}:{user.windows_user}"


async def sync_openings(
    user: PluginUserContext,
    payload: SyncOpeningsRequest,
    session: AsyncSession,
) -> SyncOpeningsResponse:
    sync_id = uuid.uuid4()
    created_by = _history_actor(user)

    existing = await openings_repo.list_openings_by_model(session, model_guid=payload.model_guid)
    existing_by_uid = {item.element_unique_id: item for item in existing}
    seen_uids: set[str] = set()

    response = SyncOpeningsResponse(sync_id=sync_id)
    items: list[SyncOpeningItemResult] = []

    for opening_payload in payload.openings:
        seen_uids.add(opening_payload.element_unique_id)
        current = existing_by_uid.get(opening_payload.element_unique_id)
        incoming = _payload_snapshot(opening_payload, payload.schedule_name)

        try:
            if current is None:
                opening = _create_opening(payload.model_guid, opening_payload, payload.schedule_name)
                session.add(opening)
                await session.flush()
                await openings_repo.add_opening_history(
                    session,
                    opening_id=opening.id,
                    event_type=OpeningHistoryEventType.CREATED,
                    payload=incoming,
                    created_by=created_by,
                )
                response.created += 1
                items.append(
                    SyncOpeningItemResult(
                        element_unique_id=opening_payload.element_unique_id,
                        result="created",
                        opening_id=opening.id,
                        status=opening.status.value,
                    )
                )
                continue

            if current.status == OpeningStatus.DELETED:
                _apply_payload(current, opening_payload, payload.schedule_name)
                current.status = OpeningStatus.NEW
                await session.flush()
                await openings_repo.add_opening_history(
                    session,
                    opening_id=current.id,
                    event_type=OpeningHistoryEventType.UPDATED,
                    payload={"restored": True, **incoming},
                    created_by=created_by,
                )
                response.updated += 1
                items.append(
                    SyncOpeningItemResult(
                        element_unique_id=opening_payload.element_unique_id,
                        result="updated",
                        opening_id=current.id,
                        status=current.status.value,
                    )
                )
                continue

            if _opening_snapshot(current) == incoming:
                response.unchanged += 1
                items.append(
                    SyncOpeningItemResult(
                        element_unique_id=opening_payload.element_unique_id,
                        result="unchanged",
                        opening_id=current.id,
                        status=current.status.value,
                    )
                )
                continue

            previous_status = current.status
            _apply_payload(current, opening_payload, payload.schedule_name)
            await session.flush()
            await openings_repo.add_opening_history(
                session,
                opening_id=current.id,
                event_type=OpeningHistoryEventType.UPDATED,
                payload=incoming,
                created_by=created_by,
            )
            response.updated += 1
            items.append(
                SyncOpeningItemResult(
                    element_unique_id=opening_payload.element_unique_id,
                    result="updated",
                    opening_id=current.id,
                    status=previous_status.value,
                )
            )
        except Exception as exc:
            logger.exception(
                "opening_sync_item_failed",
                element_unique_id=opening_payload.element_unique_id,
                error=str(exc),
            )
            response.failed += 1
            items.append(
                SyncOpeningItemResult(
                    element_unique_id=opening_payload.element_unique_id,
                    result="failed",
                    opening_id=current.id if current else None,
                    status=current.status.value if current else None,
                )
            )

    for element_unique_id, opening in existing_by_uid.items():
        if element_unique_id in seen_uids or opening.status == OpeningStatus.DELETED:
            continue

        opening.status = OpeningStatus.DELETED
        await session.flush()
        await openings_repo.add_opening_history(
            session,
            opening_id=opening.id,
            event_type=OpeningHistoryEventType.SOFT_DELETED,
            payload={"element_unique_id": element_unique_id},
            created_by=created_by,
        )
        response.soft_deleted += 1
        items.append(
            SyncOpeningItemResult(
                element_unique_id=element_unique_id,
                result="softDeleted",
                opening_id=opening.id,
                status=opening.status.value,
            )
        )

    await session.commit()
    response.items = items
    return response


async def list_openings(
    user: PluginUserContext,
    model_guid: uuid.UUID,
    session: AsyncSession,
) -> OpeningsListResponse:
    _ = user
    openings = await openings_repo.list_openings_by_model(session, model_guid=model_guid)
    return OpeningsListResponse(
        model_guid=model_guid,
        openings=[
            OpeningStatusItem(
                element_unique_id=opening.element_unique_id,
                opening_id=opening.id,
                status=opening.status.value,
                updated_at=opening.updated_at,
            )
            for opening in openings
            if opening.status != OpeningStatus.DELETED
        ],
    )
