from datetime import UTC, datetime, timedelta

import jwt
from jwt.exceptions import InvalidTokenError
from pwdlib import PasswordHash

from backend.app.config import Settings


password_hash = PasswordHash.recommended()
JWT_ALGORITHM = "HS256"
DUMMY_PASSWORD_HASH = password_hash.hash("unused-dummy-password")


class InvalidAccessToken(ValueError):
    """Raised when an access token cannot be trusted."""


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, stored_hash: str) -> bool:
    return password_hash.verify(password, stored_hash)


def create_access_token(
    user_id: int,
    settings: Settings,
    *,
    now: datetime | None = None,
) -> str:
    issued_at = now or datetime.now(UTC)
    expires_at = issued_at + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    payload = {
        "sub": str(user_id),
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "iat": issued_at,
        "exp": expires_at,
    }

    return jwt.encode(
        payload,
        settings.jwt_secret_key.get_secret_value(),
        algorithm=JWT_ALGORITHM,
    )


def decode_access_token(token: str, settings: Settings) -> int:
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key.get_secret_value(),
            algorithms=[JWT_ALGORITHM],
            audience=settings.jwt_audience,
            issuer=settings.jwt_issuer,
            options={
                "require": ["sub", "iss", "aud", "iat", "exp"],
            },
        )
        user_id = int(payload["sub"])
        if user_id <= 0:
            raise ValueError
    except (InvalidTokenError, KeyError, TypeError, ValueError):
        raise InvalidAccessToken("Invalid access token") from None

    return user_id
