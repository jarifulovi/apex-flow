import uuid
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import EntityNotFoundException
from app.core.security import UnauthorizedException
from app.main import app
from app.schemas.project_key import ProjectKeyCreate
from app.services.project_key_service import ProjectKeyService


@pytest.mark.asyncio
async def test_project_key_service_lifecycle(
    db: AsyncSession, test_user_id: uuid.UUID
):
    """
    Test service layer for Project Key creation, authentication, listing, and revocation.
    """
    # 1. Create key
    created = await ProjectKeyService.create_project_key(
        db=db,
        user_id=test_user_id,
        payload=ProjectKeyCreate(name="Staging API Key"),
    )
    assert created.name == "Staging API Key"
    assert created.user_id == test_user_id
    assert created.raw_key.startswith("af_live_")
    assert created.key_prefix.startswith("af_live_")
    assert created.status == "active"

    # 2. Authenticate valid key
    auth_user_id = await ProjectKeyService.authenticate_api_key(
        db=db, raw_key=created.raw_key
    )
    assert auth_user_id == test_user_id

    # 3. List keys
    keys = await ProjectKeyService.list_project_keys(db=db, user_id=test_user_id)
    assert len(keys) >= 1
    assert any(k.id == created.id for k in keys)

    # 4. Revoke key
    revoked = await ProjectKeyService.revoke_project_key(
        db=db, user_id=test_user_id, key_id=created.id
    )
    assert revoked.status == "revoked"

    # 5. Authenticating revoked key raises UnauthorizedException
    with pytest.raises(UnauthorizedException):
        await ProjectKeyService.authenticate_api_key(db=db, raw_key=created.raw_key)


@pytest.mark.asyncio
async def test_api_key_authentication_middleware_enforcement(
    test_user_id: uuid.UUID, test_project_key: str
):
    """
    Test HTTP endpoints reject unauthorized requests without valid X-ApexFlow-Project-Key.
    """
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        # 1. Request without header -> 401
        res = await ac.post(
            "/api/v1/workflows",
            json={"user_id": str(test_user_id), "metadata": {}},
        )
        assert res.status_code == 401

        # 2. Request with invalid key -> 401
        res_invalid = await ac.post(
            "/api/v1/workflows",
            headers={"X-ApexFlow-Project-Key": "af_live_invalid_key_12345"},
            json={"user_id": str(test_user_id), "metadata": {}},
        )
        assert res_invalid.status_code == 401

        # 3. Request with valid key -> 201
        res_valid = await ac.post(
            "/api/v1/workflows",
            headers={"X-ApexFlow-Project-Key": test_project_key},
            json={"user_id": str(test_user_id), "metadata": {}},
        )
        assert res_valid.status_code == 201
