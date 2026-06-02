from __future__ import annotations

import uvicorn
from fastapi import APIRouter, FastAPI

from app.api.routers import auth, families, family_auth, health, openings, projects
from app.core.config import get_settings
from app.core.logging import setup_logging

settings = get_settings()
setup_logging(settings.log_level)

app = FastAPI(title="Revit Families Backend", version="1.0.0")

api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(auth.router)
api_v1_router.include_router(family_auth.router)  # Rev 9: POST /api/v1/family/auth
api_v1_router.include_router(health.router)
api_v1_router.include_router(openings.router)

app.include_router(api_v1_router)
app.include_router(health.router, include_in_schema=False)
app.include_router(families.router)
app.include_router(projects.router)


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
