from __future__ import annotations

import uuid
from typing import List

from pydantic import BaseModel


class UserContext(BaseModel):
    user_id: uuid.UUID
    project_ids: List[uuid.UUID]

