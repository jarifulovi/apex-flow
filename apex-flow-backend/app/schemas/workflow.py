import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.step import WorkflowStepResponse


class WorkflowStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


# Schema to receive on workflow run creation
class WorkflowCreate(BaseModel):
    workflow_name: str = "default-workflow"
    project_id: Optional[uuid.UUID] = None
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


# Schema to receive on workflow run update
class WorkflowUpdate(BaseModel):
    status: Optional[WorkflowStatus] = None
    metadata: Optional[Dict[str, Any]] = None


# Schema for basic workflow run API response
class WorkflowResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    workflow_name: str
    status: WorkflowStatus
    metadata: Dict[str, Any] = Field(alias="metadata_")
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


# Detailed workflow API response including child steps
class WorkflowDetailResponse(WorkflowResponse):
    steps: List[WorkflowStepResponse] = []
