from collections.abc import AsyncIterator
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from backend.app.api.dependencies import get_database_session, get_rate_limiter
from backend.app.config import Settings, get_settings
from backend.app.main import app
from backend.app.services.auth import InvalidCredentials
from backend.app.services.rate_limiter import (
    RateLimitDecision,
    RateLimiterUnavailable,
)


class FakeSession:
    pass


class FakeRateLimiter:
    def __init__(self):
        self.calls = []
        self.blocked_prefix = None
        self.error = None

    async def hit(self, *, key, limit, window_seconds):
        self.calls.append((key, limit, window_seconds))
        if self.error is not None:
            raise self.error
        if self.blocked_prefix and key.startswith(self.blocked_prefix):
            return RateLimitDecision(False, 73)
        return RateLimitDecision(True, 0)

    async def close(self):
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
def rate_limiter():
    return FakeRateLimiter()


@pytest.fixture
def client(rate_limiter):
    app.dependency_overrides[get_database_session] = fake_database_session
    app.dependency_overrides[get_settings] = fake_settings
    app.dependency_overrides[get_rate_limiter] = lambda: rate_limiter

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


def test_login_returns_429_before_authentication_when_limit_is_exceeded(
    client,
    rate_limiter,
    monkeypatch,
):
    rate_limiter.blocked_prefix = "login:pair:"

    async def authentication_must_not_run(**kwargs):
        pytest.fail("Authentication ran after the rate limit was exceeded")

    monkeypatch.setattr(
        "backend.app.api.routes.auth.authenticate_user",
        authentication_must_not_run,
    )

    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "andrew@example.com",
            "password": "correct-password",
        },
    )

    assert response.status_code == 429
    assert response.json() == {"detail": "Too many login attempts"}
    assert response.headers["retry-after"] == "73"


def test_login_rate_limit_keys_do_not_contain_plain_email(
    client,
    rate_limiter,
    monkeypatch,
):
    async def reject_credentials(**kwargs):
        raise InvalidCredentials("Invalid credentials")

    monkeypatch.setattr(
        "backend.app.api.routes.auth.authenticate_user",
        reject_credentials,
    )

    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": " Andrew@Example.com ",
            "password": "wrong-password",
        },
    )

    assert response.status_code == 401
    keys = [key for key, _limit, _window in rate_limiter.calls]
    assert len(keys) == 3
    assert all("andrew@example.com" not in key.lower() for key in keys)
    assert all("testclient" not in key.lower() for key in keys)


def test_login_returns_503_when_rate_limiter_is_unavailable(
    client,
    rate_limiter,
):
    rate_limiter.error = RateLimiterUnavailable("internal Redis details")

    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "andrew@example.com",
            "password": "correct-password",
        },
    )

    assert response.status_code == 503
    assert response.json() == {
        "detail": "Authentication temporarily unavailable"
    }
    assert "Redis" not in response.text
