import pytest
from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.models.step import WorkflowStep
from app.models.workflow import Workflow


@pytest.mark.asyncio
async def test_read_only_schema_alignment_with_supabase():
    """
    Read-only test inspecting Supabase information_schema to verify
    SQLAlchemy ORM models match live database tables without inserting or deleting data.
    """
    test_engine = create_async_engine(
        settings.DATABASE_URL,
        poolclass=NullPool,
        connect_args={"statement_cache_size": 0, "prepared_statement_cache_size": 0},
    )

    def run_inspection(connection):
        inspector = inspect(connection)
        tables = inspector.get_table_names(schema="public")

        # 1. Verify core tables exist in public schema
        assert "workflows" in tables, "Table 'workflows' missing in Supabase public schema"
        assert "workflow_steps" in tables, "Table 'workflow_steps' missing in Supabase public schema"

        # 2. Inspect workflows table columns
        db_workflows_cols = {col["name"]: col for col in inspector.get_columns("workflows", schema="public")}
        for col in Workflow.__table__.columns:
            assert col.name in db_workflows_cols, f"Column '{col.name}' in Workflow model missing in Supabase"
            db_col = db_workflows_cols[col.name]
            assert db_col["nullable"] == col.nullable, f"Nullability mismatch for column '{col.name}' in workflows table"

        # 3. Inspect workflow_steps table columns
        db_steps_cols = {col["name"]: col for col in inspector.get_columns("workflow_steps", schema="public")}
        for col in WorkflowStep.__table__.columns:
            assert col.name in db_steps_cols, f"Column '{col.name}' in WorkflowStep model missing in Supabase"
            db_col = db_steps_cols[col.name]
            assert db_col["nullable"] == col.nullable, f"Nullability mismatch for column '{col.name}' in workflow_steps table"

        return True

    async with test_engine.connect() as conn:
        result = await conn.run_sync(run_inspection)
        assert result is True

    await test_engine.dispose()
