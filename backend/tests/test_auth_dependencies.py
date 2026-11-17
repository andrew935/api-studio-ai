from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from backend.app.api.dependencies import get_current_user
from backend.app.config import Settings
from backend.app.services.security import create_access_token


def make_settings() -> Settings:
    return Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        public_base_url="https://documents.example.com",
        jwt_secret_key="test-secret-key-with-at-least-32-characters",
        jwt_issuer="api-studio-ai-tests",
        jwt_audience="api-studio-ai-test-api",
        access_token_expire_minutes=30,
    )


class FakeSession:
    def __init__(self, user):
        self.user = user

    async def scalar(self, statement):
        return self.user


@pytest.mark.anyio
async def test_get_current_user_returns_database_identity():
    settings = make_settings()
    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials=create_access_token(17, settings),
    )
    session = FakeSession(
        SimpleNamespace(
            id=17,
            tenant_id=7,
            role="staff",
            is_active=True,
        )
    )

    current_user = await get_current_user(
        credentials=credentials,
        session=session,
        settings=settings,
    )

    assert current_user.user_id == 17
    assert current_user.tenant_id == 7
    assert current_user.role == "staff"


@pytest.mark.anyio
@pytest.mark.parametrize(
    "user",
    [
        None,
        SimpleNamespace(
            id=17,
            tenant_id=7,
            role="staff",
            is_active=False,
        ),
    ],
)
async def test_get_current_user_rejects_missing_or_inactive_user(user):
    settings = make_settings()
    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials=create_access_token(17, settings),
    )

    with pytest.raises(HTTPException) as error:
        await get_current_user(
            credentials=credentials,
            session=FakeSession(user),
            settings=settings,
        )

    assert error.value.status_code == 401
