import uuid
from typing import Optional
from pydantic import BaseModel, EmailStr


class UserProfile(BaseModel):
    """
    Represents the authenticated user's profile.
    All fields are sourced from the Supabase JWT claims — no DB query needed.
    """
    id: uuid.UUID
    email: Optional[str] = None
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None


class SessionResponse(BaseModel):
    """Lightweight session validity response."""
    valid: bool
    user_id: uuid.UUID
