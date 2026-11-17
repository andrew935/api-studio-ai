from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.dependencies import get_database_session
from backend.app.config import Settings, get_settings
from backend.app.schemas.auth import LoginRequest, TokenResponse
from backend.app.services.auth import InvalidCredentials, authenticate_user
from backend.app.services.security import create_access_token


router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    session: AsyncSession = Depends(get_database_session),
    settings: Settings = Depends(get_settings),
) -> TokenResponse:
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
