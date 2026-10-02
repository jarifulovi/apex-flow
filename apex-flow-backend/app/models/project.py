import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List
from sqlalchemy import DateTime, ForeignKey, String, text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.project_key import ProjectKey
    from app.models.worker import Worker
    from app.models.workflow_run import WorkflowRun


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )
    metadata_: Mapped[Dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
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

    # Relationships
    project_keys: Mapped[List["ProjectKey"]] = relationship(
        "ProjectKey",
        back_populates="project",
        cascade="all, delete-orphan",
    )
    workflow_runs: Mapped[List["WorkflowRun"]] = relationship(
        "WorkflowRun",
        back_populates="project",
        cascade="all, delete-orphan",
    )
    workers: Mapped[List["Worker"]] = relationship(
        "Worker",
        back_populates="project",
        cascade="all, delete-orphan",
    )
