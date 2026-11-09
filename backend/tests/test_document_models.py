from datetime import UTC, datetime

import pytest
from sqlalchemy import event, select
from sqlalchemy.exc import IntegrityError

from backend.app.db.base import Base
from backend.app.db.session import (
    create_database_engine,
    create_session_factory,
)
from backend.app.models.documents import (
    ClientRow,
    MatterRow,
    TenantRow,
    UploadRequestRow,
)


def enable_sqlite_foreign_keys(engine):
    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, _):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


@pytest.mark.anyio
async def test_upload_request_persists_with_matching_client_and_matter():
    engine = create_database_engine("sqlite+aiosqlite:///:memory:")
    enable_sqlite_foreign_keys(engine)

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    session_factory = create_session_factory(engine)

    async with session_factory() as session:
        tenant = TenantRow(name="Demo Law Firm")
        session.add(tenant)
        await session.flush()

        client = ClientRow(tenant_id=tenant.id, name="Demo Client")
        session.add(client)
        await session.flush()

        matter = MatterRow(
            tenant_id=tenant.id,
            client_id=client.id,
            title="Contract review",
        )
        session.add(matter)
        await session.flush()

        upload_request = UploadRequestRow(
            tenant_id=tenant.id,
            client_id=client.id,
            matter_id=matter.id,
            expires_at=datetime(2026, 12, 1, tzinfo=UTC),
            max_files=3,
        )
        session.add(upload_request)
        await session.commit()

        result = await session.execute(select(UploadRequestRow))
        stored_request = result.scalar_one()

        assert stored_request.client_id == client.id
        assert stored_request.matter_id == matter.id
        assert stored_request.status == "draft"
        assert stored_request.token_hash is None

    await engine.dispose()


@pytest.mark.anyio
async def test_upload_request_rejects_matter_from_another_client():
    engine = create_database_engine("sqlite+aiosqlite:///:memory:")
    enable_sqlite_foreign_keys(engine)

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    session_factory = create_session_factory(engine)

    async with session_factory() as session:
        tenant = TenantRow(name="Demo Law Firm")
        session.add(tenant)
        await session.flush()

        first_client = ClientRow(tenant_id=tenant.id, name="First Client")
        second_client = ClientRow(tenant_id=tenant.id, name="Second Client")
        session.add_all([first_client, second_client])
        await session.flush()

        matter = MatterRow(
            tenant_id=tenant.id,
            client_id=second_client.id,
            title="Second client's matter",
        )
        session.add(matter)
        await session.flush()

        session.add(
            UploadRequestRow(
                tenant_id=tenant.id,
                client_id=first_client.id,
                matter_id=matter.id,
                expires_at=datetime(2026, 12, 1, tzinfo=UTC),
                max_files=3,
            )
        )

        with pytest.raises(IntegrityError):
            await session.commit()

    await engine.dispose()


@pytest.mark.anyio
async def test_upload_request_rejects_active_status_without_token():
    engine = create_database_engine("sqlite+aiosqlite:///:memory:")
    enable_sqlite_foreign_keys(engine)

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    session_factory = create_session_factory(engine)

    async with session_factory() as session:
        tenant = TenantRow(name="Demo Law Firm")
        session.add(tenant)
        await session.flush()

        client = ClientRow(tenant_id=tenant.id, name="Demo Client")
        session.add(client)
        await session.flush()

        session.add(
            UploadRequestRow(
                tenant_id=tenant.id,
                client_id=client.id,
                status="active",
                expires_at=datetime(2026, 12, 1, tzinfo=UTC),
                max_files=3,
            )
        )

        with pytest.raises(IntegrityError):
            await session.commit()

    await engine.dispose()
