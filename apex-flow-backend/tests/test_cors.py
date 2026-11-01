import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import Settings
from app.main import app


def test_cors_config_parsing_comma_separated():
    """Verify comma-separated origins parse cleanly and strip trailing slashes"""
    settings = Settings(
        DATABASE_URL="postgresql://user:pass@localhost:5432/db",
        BACKEND_CORS_ORIGINS="http://localhost:3000/, http://localhost:8000",
    )
    assert settings.BACKEND_CORS_ORIGINS == ["http://localhost:3000", "http://localhost:8000"]
    assert settings.cors_allow_credentials is True


def test_cors_config_parsing_json_array():
    """Verify JSON array strings parse correctly and strip trailing slashes"""
    settings = Settings(
        DATABASE_URL="postgresql://user:pass@localhost:5432/db",
        BACKEND_CORS_ORIGINS='["http://localhost:3000/", "https://apexflow.io"]',
    )
    assert settings.BACKEND_CORS_ORIGINS == ["http://localhost:3000", "https://apexflow.io"]
    assert settings.cors_allow_credentials is True


def test_cors_config_wildcard_disables_credentials():
    """Browser security: wildcard origins must set allow_credentials to False"""
    settings = Settings(
        DATABASE_URL="postgresql://user:pass@localhost:5432/db",
        BACKEND_CORS_ORIGINS="*",
    )
    assert settings.BACKEND_CORS_ORIGINS == ["*"]
    assert settings.cors_allow_credentials is False


def test_cors_config_malformed_json_raises_error():
    """Malformed JSON should raise a clear ValueError rather than silently failing"""
    with pytest.raises(ValueError, match="Invalid JSON format"):
        Settings(
            DATABASE_URL="postgresql://user:pass@localhost:5432/db",
            BACKEND_CORS_ORIGINS="[malformed_json",
        )


@pytest.mark.asyncio
async def test_cors_preflight_allowed_origin():
    """Verify OPTIONS preflight request for allowed origin returns CORS headers"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.options(
            "/api/v1/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "Authorization,Content-Type",
            },
        )

    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"
    assert response.headers.get("access-control-allow-credentials") == "true"
    assert "GET" in response.headers.get("access-control-allow-methods", "")


@pytest.mark.asyncio
async def test_cors_regex_matches_vercel_preview():
    """Verify Vercel staging & preview deployment origins match CORS regex"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.options(
            "/api/v1/health",
            headers={
                "Origin": "https://apex-flow-git-feature-preview.vercel.app",
                "Access-Control-Request-Method": "GET",
            },
        )

    assert response.status_code == 200
    assert (
        response.headers.get("access-control-allow-origin")
        == "https://apex-flow-git-feature-preview.vercel.app"
    )
    assert response.headers.get("access-control-allow-credentials") == "true"


@pytest.mark.asyncio
async def test_cors_disallowed_origin_rejected():
    """Verify unauthorized origin does NOT receive access-control-allow-origin"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.options(
            "/api/v1/health",
            headers={
                "Origin": "https://malicious-website.com",
                "Access-Control-Request-Method": "GET",
            },
        )

    # In CORS spec, when origin is rejected, access-control-allow-origin is omitted
    assert "access-control-allow-origin" not in response.headers


@pytest.mark.asyncio
async def test_cors_simple_get_request_includes_cors_and_exposed_headers():
    """Verify actual GET request from allowed origin returns allow-origin and expose-headers"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get(
            "/api/v1/health",
            headers={"Origin": "http://localhost:3000"},
        )

    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"
    expose_headers = response.headers.get("access-control-expose-headers", "")
    assert "Content-Disposition" in expose_headers
    assert "Content-Length" in expose_headers


@pytest.mark.asyncio
async def test_security_headers_present():
    """Verify baseline HTTP security headers are included in responses"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/v1/health")

    assert response.status_code == 200
    assert response.headers.get("x-content-type-options") == "nosniff"
    assert response.headers.get("x-frame-options") == "DENY"
    assert response.headers.get("referrer-policy") == "strict-origin-when-cross-origin"


def test_docs_enabled_behavior():
    """Verify docs_enabled is disabled in production and controlled by DEBUG in other environments"""
    dev_settings = Settings(
        DATABASE_URL="postgresql://user:pass@localhost:5432/db",
        ENVIRONMENT="development",
        DEBUG=True,
    )
    assert dev_settings.docs_enabled is True

    prod_settings = Settings(
        DATABASE_URL="postgresql://user:pass@localhost:5432/db",
        ENVIRONMENT="production",
        DEBUG=True,  # Even if developer accidentally leaves DEBUG=True
    )
    assert prod_settings.docs_enabled is False

    prod_off_settings = Settings(
        DATABASE_URL="postgresql://user:pass@localhost:5432/db",
        ENVIRONMENT="production",
        DEBUG=False,
    )
    assert prod_off_settings.docs_enabled is False

