import io
import time
import uuid
import jwt
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    decode_bearer_token,
    extract_user_id,
    get_current_project_key_context,
    get_current_user_for_storage_download,
    get_current_user_from_api_key,
    get_current_user_from_headers,
    get_current_user_from_jwt,
    get_jwt_payload,
)
from app.core.config import settings
from app.core.exceptions import UnauthorizedException
from app.main import app


def _create_test_jwt(user_id: uuid.UUID, expired: bool = False) -> str:
    exp = int(time.time()) - 100 if expired else int(time.time()) + 3600
    return jwt.encode(
        {"sub": str(user_id), "exp": exp, "role": "authenticated"},
        settings.SUPABASE_JWT_SECRET,
        algorithm="HS256",
    )


# --- Unit Tests: Token Extraction & Decoding ---


def test_extract_user_id():
    valid_uuid = uuid.uuid4()
    assert extract_user_id({"sub": str(valid_uuid)}) == valid_uuid

    with pytest.raises(UnauthorizedException, match="Invalid user ID"):
        extract_user_id({"sub": "not-a-uuid"})

    with pytest.raises(UnauthorizedException, match="Invalid user ID"):
        extract_user_id({})


def test_decode_bearer_token():
    valid_uuid = uuid.uuid4()
    token = _create_test_jwt(valid_uuid)

    # Valid Bearer
    payload = decode_bearer_token(f"Bearer {token}")
    assert payload["sub"] == str(valid_uuid)

    # Missing or invalid prefixes
    with pytest.raises(UnauthorizedException, match="Missing or invalid Authorization header"):
        decode_bearer_token(None)

    with pytest.raises(UnauthorizedException, match="Missing or invalid Authorization header"):
        decode_bearer_token(f"Basic {token}")

    with pytest.raises(UnauthorizedException, match="Missing or invalid Authorization header"):
        decode_bearer_token(token)


@pytest.mark.asyncio
async def test_get_current_user_from_jwt():
    valid_uuid = uuid.uuid4()
    token = _create_test_jwt(valid_uuid)

    user_id = await get_current_user_from_jwt(authorization=f"Bearer {token}")
    assert user_id == valid_uuid

    payload = await get_jwt_payload(authorization=f"Bearer {token}")
    assert payload["sub"] == str(valid_uuid)


# --- Unit Tests: Project Key Authentication ---


@pytest.mark.asyncio
async def test_api_key_missing_header_raises(db: AsyncSession):
    with pytest.raises(UnauthorizedException, match="Missing X-ApexFlow-Project-Key header"):
        await get_current_project_key_context(x_apexflow_project_key=None, db=db)


@pytest.mark.asyncio
async def test_api_key_valid_header(db: AsyncSession, test_user_id: uuid.UUID, test_project_key: str):
    ctx = await get_current_project_key_context(
        x_apexflow_project_key=test_project_key, db=db
    )
    assert ctx.owner_id == test_user_id

    owner_id = await get_current_user_from_api_key(
        x_apexflow_project_key=test_project_key, db=db
    )
    assert owner_id == test_user_id


# --- Unit Tests: Dual-Channel Header Authentication ---


@pytest.mark.asyncio
async def test_get_current_user_from_headers_with_jwt(db: AsyncSession):
    valid_uuid = uuid.uuid4()
    token = _create_test_jwt(valid_uuid)

    owner_id = await get_current_user_from_headers(
        authorization=f"Bearer {token}", x_apexflow_project_key=None, db=db
    )
    assert owner_id == valid_uuid


@pytest.mark.asyncio
async def test_get_current_user_from_headers_with_api_key(
    db: AsyncSession, test_user_id: uuid.UUID, test_project_key: str
):
    owner_id = await get_current_user_from_headers(
        authorization=None, x_apexflow_project_key=test_project_key, db=db
    )
    assert owner_id == test_user_id


@pytest.mark.asyncio
async def test_get_current_user_from_headers_missing_both(db: AsyncSession):
    with pytest.raises(UnauthorizedException, match="Authentication required via Bearer token or X-ApexFlow-Project-Key"):
        await get_current_user_from_headers(
            authorization=None, x_apexflow_project_key=None, db=db
        )


@pytest.mark.asyncio
async def test_get_current_user_for_storage_download(
    db: AsyncSession, test_user_id: uuid.UUID, test_project_key: str
):
    valid_uuid = uuid.uuid4()
    jwt_token = _create_test_jwt(valid_uuid)

    # 1. Bearer header
    assert (
        await get_current_user_for_storage_download(
            authorization=f"Bearer {jwt_token}",
            x_apexflow_project_key=None,
            token=None,
            db=db,
        )
        == valid_uuid
    )

    # 2. X-ApexFlow-Project-Key header
    assert (
        await get_current_user_for_storage_download(
            authorization=None,
            x_apexflow_project_key=test_project_key,
            token=None,
            db=db,
        )
        == test_user_id
    )

    # 3. Query param token (browser direct download)
    assert (
        await get_current_user_for_storage_download(
            authorization=None,
            x_apexflow_project_key=None,
            token=jwt_token,
            db=db,
        )
        == valid_uuid
    )

    # 4. Missing credentials raises UnauthorizedException
    with pytest.raises(UnauthorizedException, match="Authentication required"):
        await get_current_user_for_storage_download(
            authorization=None, x_apexflow_project_key=None, token=None, db=db
        )


# --- Integration Tests: Storage Endpoints Auth & URL Safety ---


@pytest.mark.asyncio
async def test_storage_upload_and_download_flow_with_api_key(
    test_user_id: uuid.UUID, test_project_key: str
):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Upload using X-ApexFlow-Project-Key header
        payload_data = b'{"hello": "world", "timestamp": 12345}'
        files = {"file": ("test_payload.json", io.BytesIO(payload_data), "application/json")}
        headers = {"X-ApexFlow-Project-Key": test_project_key}

        upload_res = await ac.post("/api/v1/storage/upload", files=files, headers=headers)
        assert upload_res.status_code == 200
        ref = upload_res.json()
        assert ref["$apexflow_ref"] is True
        storage_key = ref["key"]

        # 2. Download using X-ApexFlow-Project-Key header (SDK method - NO key in URL)
        download_res = await ac.get(
            f"/api/v1/storage/download/{storage_key}",
            headers={"X-ApexFlow-Project-Key": test_project_key},
        )
        assert download_res.status_code == 200
        assert download_res.json() == {"hello": "world", "timestamp": 12345}

        # 3. Download using query param api_key should FAIL with 401 (API key is NEVER allowed in URL)
        forbidden_query_res = await ac.get(
            f"/api/v1/storage/download/{storage_key}?api_key={test_project_key}"
        )
        assert forbidden_query_res.status_code == 401

        # 4. Download with valid token in query param (Browser direct download)
        jwt_token = _create_test_jwt(test_user_id)
        browser_download_res = await ac.get(
            f"/api/v1/storage/download/{storage_key}?token={jwt_token}"
        )
        assert browser_download_res.status_code == 200
        assert browser_download_res.json() == {"hello": "world", "timestamp": 12345}


@pytest.mark.asyncio
async def test_storage_upload_empty_file_fails(test_project_key: str):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        files = {"file": ("empty.txt", io.BytesIO(b""), "text/plain")}
        headers = {"X-ApexFlow-Project-Key": test_project_key}

        res = await ac.post("/api/v1/storage/upload", files=files, headers=headers)
        assert res.status_code == 400
        data = res.json()
        assert data["error"]["code"] == "VALIDATION_ERROR"
        assert "Cannot upload empty file" in data["error"]["message"]


@pytest.mark.asyncio
async def test_storage_download_nonexistent_returns_404(test_project_key: str):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        headers = {"X-ApexFlow-Project-Key": test_project_key}
        res = await ac.get(
            "/api/v1/storage/download/payloads/nonexistent_file.json",
            headers=headers,
        )
        assert res.status_code == 404
        data = res.json()
        assert data["error"]["code"] == "ENTITY_NOT_FOUND"
