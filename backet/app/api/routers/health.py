from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@router.get("/healthz", include_in_schema=False)
async def health_legacy() -> dict:
    return {"status": "ok"}

