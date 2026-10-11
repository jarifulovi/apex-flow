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
    CANCELLED = "cancelled"


# Schema to receive on workflow run creation
class WorkflowCreate(BaseModel):
    workflow_name: str = "default-workflow"
    project_id: Optional[uuid.UUID] = None
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    deduplication_id: Optional[str] = None
    parent_workflow_id: Optional[uuid.UUID] = None
    forked_from_id: Optional[uuid.UUID] = None
    priority: int = Field(
        default=0, ge=-1000, le=1000, description="Workflow run priority (lower numbers execute earlier)"
    )
    timeout_seconds: Optional[int] = Field(
        default=None, ge=1, le=86400 * 30, description="Workflow execution timeout limit in seconds"
    )
    debounce_seconds: Optional[int] = Field(
        default=None, ge=1, le=86400, description="Debounce silence window in seconds before execution begins"
    )
    max_debounce_seconds: Optional[int] = Field(
        default=None, ge=1, le=86400 * 7, description="Maximum total debounce extension window before forced release"
    )


# Schema to receive on workflow run update
class WorkflowUpdate(BaseModel):
    status: Optional[WorkflowStatus] = None
    metadata: Optional[Dict[str, Any]] = None


# Schema for workflow forking request (Time-travel debugging)
class WorkflowForkRequest(BaseModel):
    from_step_order: int = Field(
        default=1, ge=1, description="Step order number from which execution will branch"
    )
    workflow_name: Optional[str] = None
    metadata_override: Optional[Dict[str, Any]] = None
    priority: Optional[int] = Field(default=None, ge=-1000, le=1000)


# Schema for basic workflow run API response
class WorkflowResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    workflow_name: str
    status: WorkflowStatus
    metadata: Dict[str, Any] = Field(alias="metadata_")
    deduplication_id: Optional[str] = None
    parent_workflow_id: Optional[uuid.UUID] = None
    forked_from_id: Optional[uuid.UUID] = None
    priority: int = 0
    timeout_seconds: Optional[int] = None
    deadline_at: Optional[datetime] = None
    debounce_seconds: Optional[int] = None
    debounced_until: Optional[datetime] = None
    debounce_deadline_at: Optional[datetime] = None
    error_message: Optional[str] = None
    steps_count: int = 0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


# Detailed workflow API response including child steps
class WorkflowDetailResponse(WorkflowResponse):
    steps: List[WorkflowStepResponse] = []
    sub_workflows: List[WorkflowResponse] = []
