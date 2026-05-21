from __future__ import annotations

import uuid
from typing import List

from pydantic import BaseModel, ConfigDict, Field


class UserContext(BaseModel):
    user_id: uuid.UUID
    project_ids: List[uuid.UUID]


class PluginUserContext(BaseModel):
    company_id: str
    windows_user: str


class AuthRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    company_id: str = Field(alias="companyId", min_length=1)
    windows_user: str = Field(alias="windowsUser", min_length=1)


class AuthResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)

    access_token: str = Field(serialization_alias="accessToken")
    expires_in: int = Field(serialization_alias="expiresIn")
