from fastapi import APIRouter, Depends, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db

router = APIRouter()


@router.get("/health", status_code=status.HTTP_200_OK)
async def health_liveness():
    """
    Lightweight liveness probe for load balancers and deployment platforms (Railway, Render).
    Responds immediately with minimal memory & CPU overhead without querying the database.
    """
    return {"status": "ok"}


@router.get("/health/db", status_code=status.HTTP_200_OK)
async def health_readiness(db: AsyncSession = Depends(get_db)):
    """
    Detailed readiness probe verifying database connection health.
    """
    db_status = "healthy"
    try:
        await db.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    return {
        "status": "online",
        "project": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "database": db_status,
    }
