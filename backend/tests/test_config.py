import pytest
from pydantic import ValidationError

from backend.app.config import Settings


def test_settings_accept_server_configuration() -> None:
    settings = Settings(
        database_url="postgresql+asyncpg://app:secret@db:5432/api_studio_ai",
        public_base_url="https://documents.example.com",
    )

    assert settings.database_url.startswith("postgresql+asyncpg://")
    assert str(settings.public_base_url) == "https://documents.example.com/"


def test_settings_reject_invalid_public_base_url() -> None:
    with pytest.raises(ValidationError):
        Settings(
            database_url="postgresql+asyncpg://app:secret@db:5432/api_studio_ai",
            public_base_url="not-a-url",
        )
