import uuid
from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, ConfigDict


class KeyStatus(str, Enum):
    ACTIVE = "active"
    REVOKED = "revoked"


class ProjectKeyCreate(BaseModel):
    name: str = "Production Key"
    project_id: Optional[uuid.UUID] = None


class ProjectKeyResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    name: str
    key_prefix: str
    status: KeyStatus
    last_used_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProjectKeyCreatedResponse(ProjectKeyResponse):
    raw_key: str  # Displayed ONCE to user upon creation
