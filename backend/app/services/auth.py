from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.users import UserRow
from backend.app.services.security import (
    DUMMY_PASSWORD_HASH,
    verify_password,
)


class InvalidCredentials(ValueError):
    """Raised without revealing which credential was invalid."""


async def authenticate_user(
    session: AsyncSession,
    email: str,
    password: str,
) -> UserRow:
    normalized_email = email.strip().lower()
    user = await session.scalar(
        select(UserRow).where(UserRow.email == normalized_email)
    )

    if user is None:
        verify_password(password, DUMMY_PASSWORD_HASH)
        raise InvalidCredentials("Invalid email or password")

    password_is_valid = verify_password(password, user.password_hash)
    if not password_is_valid or not user.is_active:
        raise InvalidCredentials("Invalid email or password")

    return user


async def load_active_user(
    session: AsyncSession,
    user_id: int,
) -> UserRow | None:
    user = await session.scalar(
        select(UserRow).where(UserRow.id == user_id)
    )
    if user is None or not user.is_active:
        return None

    return user
