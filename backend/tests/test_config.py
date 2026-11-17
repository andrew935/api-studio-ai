import pytest
from pydantic import ValidationError

from backend.app.config import Settings


def test_settings_accept_server_configuration() -> None:
    settings = Settings(
        database_url="postgresql+asyncpg://app:secret@db:5432/api_studio_ai",
        public_base_url="https://documents.example.com",
        jwt_secret_key="test-secret-key-with-at-least-32-characters",
        jwt_issuer="api-studio-ai-tests",
        jwt_audience="api-studio-ai-test-api",
        access_token_expire_minutes=30,
    )

    assert settings.database_url.startswith("postgresql+asyncpg://")
    assert str(settings.public_base_url) == "https://documents.example.com/"
    assert settings.max_upload_size_mb == 15
    assert settings.log_level == "INFO"


def test_settings_reject_invalid_public_base_url() -> None:
    with pytest.raises(ValidationError):
        Settings(
            database_url="postgresql+asyncpg://app:secret@db:5432/api_studio_ai",
            public_base_url="not-a-url",
            jwt_secret_key="test-secret-key-with-at-least-32-characters",
            jwt_issuer="api-studio-ai-tests",
            jwt_audience="api-studio-ai-test-api",
            access_token_expire_minutes=30,
        )
