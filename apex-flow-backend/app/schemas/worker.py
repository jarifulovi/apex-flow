import uuid
from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, ConfigDict


class WorkerStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class WorkerHeartbeatRequest(BaseModel):
    name: str = "default-worker"
    worker_id: Optional[uuid.UUID] = None


class WorkerResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    name: str
    status: WorkerStatus
    last_seen_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
