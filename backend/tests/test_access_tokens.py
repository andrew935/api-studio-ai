from datetime import UTC, datetime, timedelta

import jwt
import pytest

from backend.app.config import Settings
from backend.app.services.security import (
    InvalidAccessToken,
    create_access_token,
    decode_access_token,
)


def make_settings(secret: str = "test-secret-key-with-at-least-32-characters"):
    return Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        public_base_url="https://documents.example.com",
        jwt_secret_key=secret,
        jwt_issuer="api-studio-ai-tests",
        jwt_audience="api-studio-ai-test-api",
        access_token_expire_minutes=30,
    )


def test_access_token_round_trip_returns_user_id():
    settings = make_settings()

    token = create_access_token(user_id=17, settings=settings)

    assert decode_access_token(token, settings) == 17


def test_access_token_rejects_expired_token():
    settings = make_settings()
    token = create_access_token(
        user_id=17,
        settings=settings,
        now=datetime.now(UTC) - timedelta(hours=1),
    )

    with pytest.raises(InvalidAccessToken):
        decode_access_token(token, settings)


def test_access_token_rejects_wrong_signature():
    token = create_access_token(user_id=17, settings=make_settings())
    other_settings = make_settings(
        "different-test-secret-key-with-at-least-32-characters"
    )

    with pytest.raises(InvalidAccessToken):
        decode_access_token(token, other_settings)


def test_access_token_requires_subject():
    settings = make_settings()
    now = datetime.now(UTC)
    token = jwt.encode(
        {
            "iss": settings.jwt_issuer,
            "aud": settings.jwt_audience,
            "iat": now,
            "exp": now + timedelta(minutes=30),
        },
        settings.jwt_secret_key.get_secret_value(),
        algorithm="HS256",
    )

    with pytest.raises(InvalidAccessToken):
        decode_access_token(token, settings)
