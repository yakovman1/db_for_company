from __future__ import annotations

"""Best-effort audit log service (revision 8).

A failed INSERT must never break the main API operation.
"""

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
import app.db.repositories as repo

logger = get_logger(__name__)


async def log(
    session: AsyncSession,
    *,
    action: str,
    company_id: str,
    windows_user: str,
    outcome: str = "success",
    source: str = "server",
    family_id: uuid.UUID | None = None,
    family_name: str | None = None,
    original_filename: str | None = None,
    category: str | None = None,
    family_version: int | None = None,
    is_primary: bool | None = None,
    parent_family_id: uuid.UUID | None = None,
    catalog_project_id: uuid.UUID | None = None,
    revit_project_name: str | None = None,
    revit_project_path: str | None = None,
    revit_document_kind: str | None = None,
    error_message: str | None = None,
    http_status: int | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    """Insert one audit log entry. Errors are swallowed (best-effort)."""
    # Обрезаем error_message до 4000 символов (см. familylogs_spec §4.2)
    if error_message and len(error_message) > 4000:
        error_message = error_message[:4000]
    try:
        await repo.insert_log(
            session,
            action=action,
            company_id=company_id,
            windows_user=windows_user,
            outcome=outcome,
            source=source,
            family_id=family_id,
            family_name=family_name,
            original_filename=original_filename,
            category=category,
            family_version=family_version,
            is_primary=is_primary,
            parent_family_id=parent_family_id,
            catalog_project_id=catalog_project_id,
            revit_project_name=revit_project_name,
            revit_project_path=revit_project_path,
            revit_document_kind=revit_document_kind,
            error_message=error_message,
            http_status=http_status,
            details=details or {},
        )
    except Exception as exc:
        logger.warning("familylog_insert_failed", action=action, company_id=company_id,
                       windows_user=windows_user, error=str(exc))
