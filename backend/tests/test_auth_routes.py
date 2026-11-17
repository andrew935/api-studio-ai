from collections.abc import AsyncIterator
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from backend.app.api.dependencies import get_database_session
from backend.app.config import Settings, get_settings
from backend.app.main import app
from backend.app.services.auth import InvalidCredentials


class FakeSession:
    pass


async def fake_database_session() -> AsyncIterator[FakeSession]:
    yield FakeSession()


def fake_settings() -> Settings:
    return Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        public_base_url="https://documents.example.com",
        jwt_secret_key="test-secret-key-with-at-least-32-characters",
        jwt_issuer="api-studio-ai-tests",
        jwt_audience="api-studio-ai-test-api",
        access_token_expire_minutes=30,
    )


@pytest.fixture
def client():
    app.dependency_overrides[get_database_session] = fake_database_session
    app.dependency_overrides[get_settings] = fake_settings

    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()


def test_login_returns_bearer_token(client, monkeypatch):
    async def fake_authenticate_user(**kwargs):
        assert kwargs["email"] == "andrew@example.com"
        assert kwargs["password"] == "correct-password"
        return SimpleNamespace(id=17)

    monkeypatch.setattr(
        "backend.app.api.routes.auth.authenticate_user",
        fake_authenticate_user,
    )
    monkeypatch.setattr(
        "backend.app.api.routes.auth.create_access_token",
        lambda **kwargs: "signed-access-token",
    )

    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "andrew@example.com",
            "password": "correct-password",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "access_token": "signed-access-token",
        "token_type": "bearer",
    }


def test_login_hides_invalid_credential_reason(client, monkeypatch):
    async def reject_credentials(**kwargs):
        raise InvalidCredentials("specific internal reason")

    monkeypatch.setattr(
        "backend.app.api.routes.auth.authenticate_user",
        reject_credentials,
    )

    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "unknown@example.com",
            "password": "wrong-password",
        },
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid email or password"}
    assert response.headers["www-authenticate"] == "Bearer"


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"email": "a", "password": "correct-password"},
        {"email": "andrew@example.com", "password": "short"},
    ],
)
def test_login_rejects_invalid_payload(client, payload):
    response = client.post("/api/v1/auth/login", json=payload)

    assert response.status_code == 422
