import pytest
from sqlalchemy import event, func, select

from backend.app.db.base import Base
from backend.app.db.session import (
    create_database_engine,
    create_session_factory,
)
from backend.app.models.documents import TenantRow
from backend.app.models.users import UserRow
from backend.app.services.bootstrap import (
    BootstrapAdminConflict,
    bootstrap_admin,
)
from backend.app.services.security import verify_password


def enable_sqlite_foreign_keys(engine):
    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, _):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


@pytest.mark.anyio
async def test_bootstrap_creates_tenant_and_admin_atomically():
    engine = create_database_engine("sqlite+aiosqlite:///:memory:")
    enable_sqlite_foreign_keys(engine)

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    session_factory = create_session_factory(engine)

    async with session_factory() as session:
        result = await bootstrap_admin(
            session,
            tenant_name="  Demo Law Firm  ",
            email="  Admin@Example.COM  ",
            password="correct-password",
        )
        user = await session.scalar(select(UserRow))

        assert user is not None
        assert result.tenant_id == user.tenant_id
        assert result.user_id == user.id
        assert result.email == "admin@example.com"
        assert user.role == "admin"
        assert verify_password("correct-password", user.password_hash)

    await engine.dispose()


@pytest.mark.anyio
async def test_bootstrap_rolls_back_tenant_when_admin_email_conflicts():
    engine = create_database_engine("sqlite+aiosqlite:///:memory:")
    enable_sqlite_foreign_keys(engine)

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    session_factory = create_session_factory(engine)

    async with session_factory() as session:
        await bootstrap_admin(
            session,
            tenant_name="First Law Firm",
            email="admin@example.com",
            password="correct-password",
        )

        with pytest.raises(BootstrapAdminConflict):
            await bootstrap_admin(
                session,
                tenant_name="Orphan Law Firm",
                email="admin@example.com",
                password="another-password",
            )

        tenant_count = await session.scalar(
            select(func.count()).select_from(TenantRow)
        )
        assert tenant_count == 1

    await engine.dispose()
