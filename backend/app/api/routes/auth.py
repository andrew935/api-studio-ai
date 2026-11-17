from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.dependencies import get_database_session, get_rate_limiter
from backend.app.config import Settings, get_settings
from backend.app.schemas.auth import LoginRequest, TokenResponse
from backend.app.services.auth import InvalidCredentials, authenticate_user
from backend.app.services.security import create_access_token
from backend.app.services.rate_limiter import (
    RateLimiter,
    RateLimiterUnavailable,
    check_login_limits,
    create_email_identifier,
    create_ip_identifier,
)


router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    http_request: Request,
    session: AsyncSession = Depends(get_database_session),
    settings: Settings = Depends(get_settings),
    rate_limiter: RateLimiter = Depends(get_rate_limiter),
) -> TokenResponse:
    client_ip = http_request.client.host if http_request.client else "unknown"
    email_identifier = create_email_identifier(
        request.email,
        settings.rate_limit_hmac_key.get_secret_value(),
    )
    client_ip_identifier = create_ip_identifier(
        client_ip,
        settings.rate_limit_hmac_key.get_secret_value(),
    )

    try:
        decision = await check_login_limits(
            rate_limiter=rate_limiter,
            client_ip_identifier=client_ip_identifier,
            email_identifier=email_identifier,
            settings=settings,
        )
    except RateLimiterUnavailable:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication temporarily unavailable",
        )

    if not decision.allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts",
            headers={"Retry-After": str(decision.retry_after_seconds)},
        )

    try:
        user = await authenticate_user(
            session=session,
            email=request.email,
            password=request.password,
        )
    except InvalidCredentials:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(
        user_id=user.id,
        settings=settings,
    )
    return TokenResponse(access_token=access_token)
