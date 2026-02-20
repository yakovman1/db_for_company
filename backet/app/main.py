from __future__ import annotations

import uvicorn
from fastapi import FastAPI

from app.api.routers import families, health, projects
from app.core.config import get_settings
from app.core.logging import setup_logging

settings = get_settings()
setup_logging(settings.log_level)

app = FastAPI(title="Revit Families Backend", version="1.0.0")


app.include_router(health.router)
app.include_router(families.router)
app.include_router(projects.router)


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)

