import pytest
from sqlalchemy import event

from backend.app.db.base import Base
from backend.app.db.session import (
    create_database_engine,
    create_session_factory,
)
from backend.app.models.documents import TenantRow
from backend.app.models.users import UserRow
from backend.app.services.auth import InvalidCredentials, authenticate_user
from backend.app.services.security import hash_password


def enable_sqlite_foreign_keys(engine):
    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, _):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


async def create_user_session(
    *,
    is_active: bool = True,
):
    engine = create_database_engine("sqlite+aiosqlite:///:memory:")
    enable_sqlite_foreign_keys(engine)

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    session_factory = create_session_factory(engine)
    session = session_factory()
    tenant = TenantRow(name="Demo Law Firm")
    session.add(tenant)
    await session.flush()
    session.add(
        UserRow(
            tenant_id=tenant.id,
            email="andrew@example.com",
            password_hash=hash_password("correct-password"),
            is_active=is_active,
        )
    )
    await session.commit()
    return engine, session


@pytest.mark.anyio
async def test_authenticate_user_normalizes_email_and_accepts_password():
    engine, session = await create_user_session()

    try:
        user = await authenticate_user(
            session,
            email="  Andrew@Example.COM  ",
            password="correct-password",
        )

        assert user.email == "andrew@example.com"
    finally:
        await session.close()
        await engine.dispose()


@pytest.mark.anyio
async def test_authenticate_user_rejects_wrong_password():
    engine, session = await create_user_session()

    try:
        with pytest.raises(InvalidCredentials):
            await authenticate_user(
                session,
                email="andrew@example.com",
                password="wrong-password",
            )
    finally:
        await session.close()
        await engine.dispose()


@pytest.mark.anyio
async def test_authenticate_user_rejects_unknown_email():
    engine, session = await create_user_session()

    try:
        with pytest.raises(InvalidCredentials):
            await authenticate_user(
                session,
                email="unknown@example.com",
                password="wrong-password",
            )
    finally:
        await session.close()
        await engine.dispose()


@pytest.mark.anyio
async def test_authenticate_user_rejects_inactive_user():
    engine, session = await create_user_session(is_active=False)

    try:
        with pytest.raises(InvalidCredentials):
            await authenticate_user(
                session,
                email="andrew@example.com",
                password="correct-password",
            )
    finally:
        await session.close()
        await engine.dispose()
