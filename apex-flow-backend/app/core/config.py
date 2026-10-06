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

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            return v
        return []

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
