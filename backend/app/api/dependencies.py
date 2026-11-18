from collections.abc import AsyncIterator
from dataclasses import dataclass

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from openai import AsyncOpenAI

from backend.app.config import Settings, get_settings
from backend.app.models.users import UserRole
from backend.app.services.auth import load_active_user
from backend.app.services.security import (
    InvalidAccessToken,
    decode_access_token,
)
from backend.app.services.file_storage import FileStorage
from backend.app.services.llm_client import create_openai_client
from backend.app.services.rate_limiter import RateLimiter


bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class AuthenticatedUser:
    user_id: int
    tenant_id: int
    role: UserRole


def authentication_error() -> HTTPException:
    return HTTPException(
        status_code=401,
        detail="Authentication required",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_database_session(
    request: Request,
) -> AsyncIterator[AsyncSession]:
    session_factory = request.app.state.database_session_factory

    async with session_factory() as session:
        yield session


def get_file_storage(request: Request) -> FileStorage:
    return request.app.state.file_storage


def get_rate_limiter(request: Request) -> RateLimiter:
    return request.app.state.rate_limiter


def get_openai_client(
    settings: Settings = Depends(get_settings),
) -> AsyncOpenAI:
    return create_openai_client(
        timeout=settings.openai_attempt_timeout_seconds,
        max_retries=settings.openai_max_retries,
    )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    session: AsyncSession = Depends(get_database_session),
    settings: Settings = Depends(get_settings),
) -> AuthenticatedUser:
    if credentials is None:
        raise authentication_error()

    try:
        user_id = decode_access_token(credentials.credentials, settings)
    except InvalidAccessToken:
        raise authentication_error()

    user = await load_active_user(session, user_id)
    if user is None:
        raise authentication_error()

    return AuthenticatedUser(
        user_id=user.id,
        tenant_id=user.tenant_id,
        role=user.role,
    )


def get_current_tenant_id(
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> int:
    return current_user.tenant_id
