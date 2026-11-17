import pytest
from sqlalchemy import event, select
from sqlalchemy.exc import IntegrityError

from backend.app.db.base import Base
from backend.app.db.session import (
    create_database_engine,
    create_session_factory,
)
from backend.app.models.documents import TenantRow
from backend.app.models.users import UserRow


def enable_sqlite_foreign_keys(engine):
    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, _):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


@pytest.mark.anyio
async def test_user_uses_staff_and_active_defaults():
    engine = create_database_engine("sqlite+aiosqlite:///:memory:")
    enable_sqlite_foreign_keys(engine)

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    session_factory = create_session_factory(engine)

    async with session_factory() as session:
        tenant = TenantRow(name="Demo Law Firm")
        session.add(tenant)
        await session.flush()

        session.add(
            UserRow(
                tenant_id=tenant.id,
                email="employee@example.com",
                password_hash="$argon2id$example",
            )
        )
        await session.commit()

        stored_user = await session.scalar(select(UserRow))

        assert stored_user is not None
        assert stored_user.role == "staff"
        assert stored_user.is_active is True

    await engine.dispose()


@pytest.mark.anyio
async def test_user_email_is_globally_unique():
    engine = create_database_engine("sqlite+aiosqlite:///:memory:")
    enable_sqlite_foreign_keys(engine)

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    session_factory = create_session_factory(engine)

    async with session_factory() as session:
        first_tenant = TenantRow(name="First Law Firm")
        second_tenant = TenantRow(name="Second Law Firm")
        session.add_all([first_tenant, second_tenant])
        await session.flush()

        session.add(
            UserRow(
                tenant_id=first_tenant.id,
                email="employee@example.com",
                password_hash="$argon2id$first",
            )
        )
        await session.commit()

        session.add(
            UserRow(
                tenant_id=second_tenant.id,
                email="employee@example.com",
                password_hash="$argon2id$second",
            )
        )

        with pytest.raises(IntegrityError):
            await session.commit()

    await engine.dispose()


@pytest.mark.anyio
async def test_user_rejects_unknown_role():
    engine = create_database_engine("sqlite+aiosqlite:///:memory:")
    enable_sqlite_foreign_keys(engine)

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    session_factory = create_session_factory(engine)

    async with session_factory() as session:
        tenant = TenantRow(name="Demo Law Firm")
        session.add(tenant)
        await session.flush()

        session.add(
            UserRow(
                tenant_id=tenant.id,
                email="employee@example.com",
                password_hash="$argon2id$example",
                role="owner",
            )
        )

        with pytest.raises(IntegrityError):
            await session.commit()

    await engine.dispose()
