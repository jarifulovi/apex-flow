from datetime import datetime
from typing import TYPE_CHECKING, Optional
import uuid
from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.project import Project


class WorkflowSchedule(Base):
    __tablename__ = "workflow_schedules"
    __table_args__ = (
        UniqueConstraint("project_id", "workflow_name", name="uq_workflow_schedules_project_workflow"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    workflow_name: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )
    cron_expression: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )
    timezone: Mapped[str] = mapped_column(
        String,
        nullable=False,
        default="UTC",
        server_default=text("'UTC'::text"),
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )
    next_run_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    last_run_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
        onupdate=datetime.now,
    )

    # Relationship to project
    project: Mapped["Project"] = relationship(
        "Project",
        back_populates="workflow_schedules",
    )

