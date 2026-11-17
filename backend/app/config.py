from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, HttpUrl, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    public_base_url: HttpUrl
    jwt_secret_key: SecretStr = Field(min_length=32)
    jwt_issuer: str = Field(min_length=1)
    jwt_audience: str = Field(min_length=1)
    access_token_expire_minutes: int = Field(ge=5, le=1440)
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    mcp_server_url: HttpUrl = HttpUrl("http://localhost:8001/mcp")
    mcp_auth_issuer_url: HttpUrl = HttpUrl("http://localhost:8000")
    mcp_bind_host: str = "127.0.0.1"
    mcp_bind_port: int = Field(default=8001, ge=1, le=65535)
    upload_session_audience: str = "api-studio-ai-upload"
    upload_session_expire_minutes: int = Field(default=30, ge=5, le=120)
    upload_cookie_secure: bool = True
    storage_backend: Literal["local", "s3"] = "local"
    local_storage_path: Path = Path("storage/uploads")
    max_upload_size_mb: int = Field(default=15, ge=1, le=100)
    s3_bucket: str | None = None
    s3_region: str = "us-east-1"
    s3_endpoint_url: HttpUrl | None = None
    s3_circuit_failure_threshold: int = Field(default=3, ge=1, le=20)
    s3_circuit_recovery_seconds: int = Field(default=30, ge=1, le=3600)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
