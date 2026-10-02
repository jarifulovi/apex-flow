import uuid
from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict, Field


class ProjectCreate(BaseModel):
    name: str = "My Project"
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class ProjectResponse(BaseModel):
    id: uuid.UUID
    owner_id: uuid.UUID
    name: str
    metadata: Dict[str, Any] = Field(alias="metadata_")
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class ProjectKeyContext(BaseModel):
    project_id: uuid.UUID
    owner_id: uuid.UUID
    key_id: uuid.UUID
