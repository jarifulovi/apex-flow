from fastapi import APIRouter

from app.api.v1 import auth, health, project_keys, projects, steps, storage, workers, workflows

api_router = APIRouter()
api_router.include_router(health.router, tags=["Health"])
api_router.include_router(auth.router, tags=["Auth"])
api_router.include_router(projects.router, tags=["Projects"])
api_router.include_router(project_keys.router, tags=["Project Keys"])
api_router.include_router(workers.router, tags=["Workers"])
api_router.include_router(workflows.router, tags=["Workflows"])
api_router.include_router(steps.router, tags=["Steps"])
api_router.include_router(storage.router, tags=["Storage"])

