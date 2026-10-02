import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class StepStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


# Schema to create a new step
class WorkflowStepCreate(BaseModel):
    workflow_id: uuid.UUID  # Accepts workflow_id or workflow_run_id
    step_name: str
    input_payload: Optional[Dict[str, Any]] = Field(default_factory=dict)
    max_attempts: int = 3


# Schema for worker poll request
class StepPollRequest(BaseModel):
    step_names: Optional[List[str]] = None
    lock_duration_seconds: int = Field(default=300, ge=5, le=3600)
    worker_id: Optional[uuid.UUID] = None
    worker_name: Optional[str] = "python-worker"


# Payload sent by SDK worker when reporting step execution status
class StepReportPayload(BaseModel):
    step_id: uuid.UUID
    status: StepStatus
    output_payload: Optional[Dict[str, Any]] = Field(default_factory=dict)
    error_message: Optional[str] = None


# Schema for step response API objects
class WorkflowStepResponse(BaseModel):
    id: uuid.UUID
    workflow_run_id: uuid.UUID
    step_name: str
    status: StepStatus
    attempt_count: int
    max_attempts: int
    locked_until: Optional[datetime] = None
    input_payload: Dict[str, Any]
    output_payload: Dict[str, Any]
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
