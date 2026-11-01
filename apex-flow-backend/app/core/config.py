import json
from typing import List, Optional, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "ApexFlow Control Plane"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"

    # Environment mode: development, staging, production
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    DB_ECHO: bool = False

    # Cloud deployment PORT (Railway / Render inject $PORT)
    PORT: int = 8000

    # Supabase JWT Secret & JWKS URL for verifying Dashboard JWTs
    SUPABASE_JWT_SECRET: Optional[str] = None
    SUPABASE_JWKS_URL: Optional[str] = None
    SUPABASE_SERVICE_KEY: Optional[str] = None
    SUPABASE_PUB_KEY: Optional[str] = None
    SUPABASE_SECRET_KEY: Optional[str] = None

    # Database connection URL (Required in environment / .env)
    DATABASE_URL: str
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 3
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 300

    # Storage settings for offloaded payloads (>250KB up to 2MB control plane ceiling)
    PAYLOAD_MAX_INLINE_BYTES: int = 250 * 1024  # 250 KB inline threshold
    PAYLOAD_MAX_SINGLE_BYTES: int = 2 * 1024 * 1024  # 2 MB control-plane payload limit
    STORAGE_PROVIDER: str = "local"  # "local" or "s3"
    STORAGE_LOCAL_DIR: str = ".apexflow_storage"
    S3_BUCKET_NAME: Optional[str] = None
    S3_ENDPOINT_URL: Optional[str] = None
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_REGION: str = "us-east-1"


    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_db_connection(cls, v: str) -> str:
        if isinstance(v, str):
            # Handle Railway & Render default Postgres URLs (postgres:// or postgresql://)
            if v.startswith("postgres://"):
                return v.replace("postgres://", "postgresql+asyncpg://", 1)
            elif v.startswith("postgresql://") and not v.startswith("postgresql+asyncpg://"):
                return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v

    # CORS origins: can be passed as JSON list or comma-separated string in ENV
    BACKEND_CORS_ORIGINS: Union[List[str], str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ]
    CORS_ORIGIN_REGEX: Optional[str] = r"https://.*\.vercel\.app"
    CORS_ALLOW_METHODS: Union[List[str], str] = ["*"]
    CORS_ALLOW_HEADERS: Union[List[str], str] = ["*"]
    CORS_EXPOSE_HEADERS: Union[List[str], str] = [
        "Content-Disposition",
        "Content-Length",
        "X-Request-ID",
    ]

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        origins: List[str] = []
        if isinstance(v, str):
            v_str = v.strip()
            if not v_str:
                return []
            if v_str.startswith("["):
                try:
                    parsed = json.loads(v_str)
                    if not isinstance(parsed, list):
                        raise ValueError("JSON in BACKEND_CORS_ORIGINS must be a list of origin strings")
                    origins = [str(item).strip().rstrip("/") for item in parsed if str(item).strip()]
                except json.JSONDecodeError as err:
                    raise ValueError(f"Invalid JSON format for BACKEND_CORS_ORIGINS: {err}") from err
            else:
                origins = [item.strip().rstrip("/") for item in v_str.split(",") if item.strip()]
        elif isinstance(v, (list, tuple, set)):
            origins = [str(item).strip().rstrip("/") for item in v if str(item).strip()]
        else:
            raise ValueError(f"BACKEND_CORS_ORIGINS must be a list or delimited string, got {type(v).__name__}")

        # Deduplicate while preserving order
        seen = set()
        deduped = []
        for origin in origins:
            if origin not in seen:
                seen.add(origin)
                deduped.append(origin)
        return deduped

    @field_validator("CORS_ORIGIN_REGEX", mode="before")
    @classmethod
    def assemble_cors_regex(cls, v: Optional[str]) -> Optional[str]:
        if not v or not v.strip():
            return None
        return v.strip()

    @field_validator("CORS_EXPOSE_HEADERS", "CORS_ALLOW_METHODS", "CORS_ALLOW_HEADERS", mode="before")
    @classmethod
    def assemble_cors_headers(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            v_str = v.strip()
            if not v_str:
                return []
            if v_str.startswith("["):
                try:
                    parsed = json.loads(v_str)
                    if isinstance(parsed, list):
                        return [str(item).strip() for item in parsed if str(item).strip()]
                    raise ValueError("JSON must be a list of header strings")
                except json.JSONDecodeError as err:
                    raise ValueError(f"Invalid JSON header list: {err}") from err
            return [item.strip() for item in v_str.split(",") if item.strip()]
        elif isinstance(v, (list, tuple, set)):
            return [str(item).strip() for item in v if str(item).strip()]
        return []

    @property
    def cors_allow_credentials(self) -> bool:
        # Browser security specification: allow_credentials cannot be True if allow_origins contains "*"
        return "*" not in self.BACKEND_CORS_ORIGINS

    @property
    def docs_enabled(self) -> bool:
        # Enabled in dev/staging if DEBUG is True, but strictly disabled in production
        return bool(self.DEBUG and (self.ENVIRONMENT or "").strip().lower() != "production")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
