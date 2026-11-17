from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import jwt
from jwt.exceptions import InvalidTokenError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config import Settings
from backend.app.models.documents import UploadRequestRow
from backend.app.services.security import JWT_ALGORITHM
from backend.app.services.upload_tokens import hash_upload_token


UPLOAD_SESSION_TOKEN_TYPE = "upload_session"


class UploadLinkUnavailable(LookupError):
    """Raised without revealing why a public upload link is unavailable."""


class InvalidUploadSession(ValueError):
    """Raised when an upload-session cookie cannot be trusted."""


@dataclass(frozen=True)
class ValidatedUploadLink:
    upload_request_id: int
    expires_at: datetime


@dataclass(frozen=True)
class CreatedUploadSession:
    token: str
    expires_at: datetime


def as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


async def validate_upload_link(
    session: AsyncSession,
    raw_token: str,
    *,
    now: datetime | None = None,
) -> ValidatedUploadLink:
    checked_at = now or datetime.now(UTC)
    result = await session.execute(
        select(
            UploadRequestRow.id,
            UploadRequestRow.expires_at,
        ).where(
            UploadRequestRow.token_hash == hash_upload_token(raw_token),
            UploadRequestRow.status == "active",
            UploadRequestRow.expires_at > checked_at,
        )
    )
    row = result.one_or_none()
    if row is None:
        raise UploadLinkUnavailable("Upload link not found or unavailable")

    return ValidatedUploadLink(
        upload_request_id=row.id,
        expires_at=as_utc(row.expires_at),
    )


def create_upload_session(
    upload_link: ValidatedUploadLink,
    settings: Settings,
    *,
    now: datetime | None = None,
) -> CreatedUploadSession:
    issued_at = now or datetime.now(UTC)
    normal_expiration = issued_at + timedelta(
        minutes=settings.upload_session_expire_minutes
    )
    expires_at = min(normal_expiration, as_utc(upload_link.expires_at))
    if expires_at <= issued_at:
        raise UploadLinkUnavailable("Upload link not found or unavailable")

    payload = {
        "sub": str(upload_link.upload_request_id),
        "iss": settings.jwt_issuer,
        "aud": settings.upload_session_audience,
        "iat": issued_at,
        "exp": expires_at,
        "token_type": UPLOAD_SESSION_TOKEN_TYPE,
    }
    token = jwt.encode(
        payload,
        settings.jwt_secret_key.get_secret_value(),
        algorithm=JWT_ALGORITHM,
    )
    return CreatedUploadSession(token=token, expires_at=expires_at)


def decode_upload_session(token: str, settings: Settings) -> int:
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key.get_secret_value(),
            algorithms=[JWT_ALGORITHM],
            audience=settings.upload_session_audience,
            issuer=settings.jwt_issuer,
            options={
                "require": [
                    "sub",
                    "iss",
                    "aud",
                    "iat",
                    "exp",
                    "token_type",
                ]
            },
        )
        if payload["token_type"] != UPLOAD_SESSION_TOKEN_TYPE:
            raise ValueError
        upload_request_id = int(payload["sub"])
        if upload_request_id <= 0:
            raise ValueError
    except (InvalidTokenError, KeyError, TypeError, ValueError):
        raise InvalidUploadSession("Invalid upload session") from None

    return upload_request_id
