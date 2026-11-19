from datetime import datetime
from typing import List, Optional
import uuid
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from croniter import croniter
from pydantic import BaseModel, ConfigDict, Field, field_validator


def validate_workflow_name(value: str) -> str:
    """Validate and normalize a non-empty workflow name."""
    cleaned = (value or "").strip()
    if not cleaned:
        raise ValueError("workflow_name must be a non-empty string.")
    return cleaned


def validate_cron_expression(value: str) -> str:
    """Validate that a cron string is a standard 5-field expression accepted by croniter."""
    cleaned = " ".join((value or "").strip().split())
    if len(cleaned.split(" ")) != 5 or not croniter.is_valid(cleaned):
        raise ValueError(f"Invalid 5-field cron expression: '{value}'.")
    return cleaned


def validate_timezone_name(value: str) -> str:
    """Validate that a timezone name resolves cleanly via Python zoneinfo."""
    cleaned = (value or "").strip()
    if not cleaned:
        raise ValueError("timezone must not be empty.")
    try:
        ZoneInfo(cleaned)
    except (ZoneInfoNotFoundError, KeyError, ValueError):
        raise ValueError(f"Invalid IANA timezone: '{value}'.")
    return cleaned


class ScheduleCreate(BaseModel):
    """Schema for creating a new recurring workflow schedule."""

    model_config = ConfigDict(extra="forbid")

    workflow_name: str = Field(..., min_length=1, max_length=255)
    cron_expression: str
    timezone: str = Field(default="UTC")
    is_active: bool = Field(default=True)

    @field_validator("workflow_name")
    @classmethod
    def check_workflow_name(cls, v: str) -> str:
        return validate_workflow_name(v)

    @field_validator("cron_expression")
    @classmethod
    def check_cron_expression(cls, v: str) -> str:
        return validate_cron_expression(v)

    @field_validator("timezone")
    @classmethod
    def check_timezone(cls, v: str) -> str:
        return validate_timezone_name(v)


class ScheduleUpdate(BaseModel):
    """Schema for partially updating an existing workflow schedule."""

    model_config = ConfigDict(extra="forbid")

    workflow_name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    cron_expression: Optional[str] = None
    timezone: Optional[str] = None
    is_active: Optional[bool] = None

    @field_validator("workflow_name")
    @classmethod
    def check_workflow_name(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        return validate_workflow_name(v)

    @field_validator("cron_expression")
    @classmethod
    def check_cron_expression(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        return validate_cron_expression(v)

    @field_validator("timezone")
    @classmethod
    def check_timezone(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        return validate_timezone_name(v)


class WorkerScheduleDeclaration(BaseModel):
    """Cron schedule declared via the worker SDK @client.workflow decorator."""

    model_config = ConfigDict(extra="forbid")

    workflow_name: str = Field(..., min_length=1, max_length=255)
    cron_expression: str
    timezone: str = Field(default="UTC")

    @field_validator("workflow_name")
    @classmethod
    def check_workflow_name(cls, v: str) -> str:
        return validate_workflow_name(v)

    @field_validator("cron_expression")
    @classmethod
    def check_cron_expression(cls, v: str) -> str:
        return validate_cron_expression(v)

    @field_validator("timezone")
    @classmethod
    def check_timezone(cls, v: str) -> str:
        return validate_timezone_name(v)


class ScheduleSyncRequest(BaseModel):
    """Payload submitted by workers on startup to register declared schedules."""

    model_config = ConfigDict(extra="forbid")

    schedules: List[WorkerScheduleDeclaration] = Field(default_factory=list)


class ScheduleResponse(BaseModel):
    """Serialized workflow schedule record."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    workflow_name: str
    cron_expression: str
    timezone: str
    is_active: bool
    next_run_at: Optional[datetime] = None
    last_run_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class ScheduleTriggerResponse(BaseModel):
    """Response returned when a schedule is manually triggered via Run Now."""

    schedule: ScheduleResponse
    workflow_run_id: uuid.UUID

