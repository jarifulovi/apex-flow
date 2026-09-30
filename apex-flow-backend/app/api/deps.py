import uuid
from typing import Optional
from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import UnauthorizedException, decode_supabase_jwt
from app.services.project_key_service import ProjectKeyService


async def get_current_user_from_api_key(
    x_apexflow_project_key: Optional[str] = Header(None, alias="X-ApexFlow-Project-Key"),
    db: AsyncSession = Depends(get_db),
) -> uuid.UUID:
    """
    Dependency for SDK/Worker endpoints.
    Authenticates requests via the X-ApexFlow-Project-Key header.
    Returns the associated user_id.
    """
    if not x_apexflow_project_key:
        raise UnauthorizedException("Missing X-ApexFlow-Project-Key header.")

    return await ProjectKeyService.authenticate_api_key(
        db=db, raw_key=x_apexflow_project_key
    )


async def get_current_user_from_jwt(
    authorization: Optional[str] = Header(None),
) -> uuid.UUID:
    """
    Dependency for Dashboard UI endpoints.
    Authenticates requests via the Bearer Supabase JWT in Authorization header.
    Returns user_id (sub claim).
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise UnauthorizedException("Missing or invalid Authorization header.")

    token = authorization.split("Bearer ", 1)[1].strip()
    payload = decode_supabase_jwt(token)
    user_id_str = payload.get("sub")

    try:
        return uuid.UUID(user_id_str)
    except (ValueError, TypeError):
        raise UnauthorizedException("Invalid user ID in JWT sub claim.")
