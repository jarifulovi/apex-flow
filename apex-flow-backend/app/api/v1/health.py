from fastapi import APIRouter, Depends, Response, status
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
async def health_readiness(response: Response, db: AsyncSession = Depends(get_db)):
    """
    Detailed readiness probe verifying database connection health.
    Returns HTTP 200 OK when online, or HTTP 503 Service Unavailable when DB is down.
    """
    db_status = "healthy"
    system_status = "online"
    try:
        await db.execute(text("SELECT 1"))
    except Exception as e:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        system_status = "degraded"
        db_status = f"unhealthy: {str(e)}"

    return {
        "status": system_status,
        "project": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "database": db_status,
    }
