from fastapi import APIRouter

from app.api.v1 import health, steps, workflows

api_router = APIRouter()
api_router.include_router(health.router, tags=["Health"])
api_router.include_router(workflows.router, tags=["Workflows"])
api_router.include_router(steps.router, tags=["Steps"])
