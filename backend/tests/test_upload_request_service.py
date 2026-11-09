import pytest
from datetime import UTC, datetime
from sqlalchemy import event

from backend.app.db.base import Base
from backend.app.db.session import (
    create_database_engine,
    create_session_factory,
)
from backend.app.models.documents import ClientRow, TenantRow, UploadRequestRow
from backend.app.services.upload_tokens import upload_token_matches

from backend.app.services.upload_requests import (
    InvalidUploadRequestStatusTransition,
    UploadRequestActivationConflict,
    UploadRequestNotFound,
    activate_upload_request,
    validate_status_transition,
)


def enable_sqlite_foreign_keys(engine):
    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, _):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


@pytest.mark.parametrize(
    ("current_status", "target_status"),
    [
        ("draft", "active"),
        ("draft", "revoked"),
        ("active", "completed"),
        ("active", "expired"),
        ("active", "revoked"),
    ],
)
def test_validate_status_transition_accepts_allowed_transition(
    current_status,
    target_status,
):
    assert validate_status_transition(current_status, target_status) is True


def test_validate_status_transition_treats_retry_as_idempotent():
    assert validate_status_transition("active", "active") is False


@pytest.mark.parametrize(
    ("current_status", "target_status"),
    [
        ("draft", "completed"),
        ("completed", "active"),
        ("expired", "active"),
        ("revoked", "active"),
    ],
)
def test_validate_status_transition_rejects_invalid_transition(
    current_status,
    target_status,
):
    with pytest.raises(
        InvalidUploadRequestStatusTransition,
        match=f"from {current_status} to {target_status}",
    ):
        validate_status_transition(current_status, target_status)


@pytest.mark.anyio
async def test_activate_upload_request_commits_status_and_token_together():
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

        upload_request = UploadRequestRow(
            tenant_id=tenant.id,
            client_id=client.id,
            expires_at=datetime(2026, 12, 1, tzinfo=UTC),
            max_files=3,
        )
        session.add(upload_request)
        await session.commit()

        activation = await activate_upload_request(
            session,
            tenant_id=tenant.id,
            upload_request_id=upload_request.id,
        )
        await session.refresh(upload_request)

        assert upload_request.status == "active"
        assert upload_request.token_hash is not None
        assert activation.upload_request_id == upload_request.id
        assert activation.expires_at == upload_request.expires_at
        assert upload_token_matches(
            activation.raw_token,
            upload_request.token_hash,
        )
        assert activation.raw_token != upload_request.token_hash

    await engine.dispose()


@pytest.mark.anyio
async def test_activate_upload_request_rejects_non_draft_request():
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

        upload_request = UploadRequestRow(
            tenant_id=tenant.id,
            client_id=client.id,
            status="revoked",
            expires_at=datetime(2026, 12, 1, tzinfo=UTC),
            max_files=3,
        )
        session.add(upload_request)
        await session.commit()

        with pytest.raises(UploadRequestActivationConflict):
            await activate_upload_request(
                session,
                tenant_id=tenant.id,
                upload_request_id=upload_request.id,
            )

        await session.refresh(upload_request)
        assert upload_request.status == "revoked"
        assert upload_request.token_hash is None

    await engine.dispose()


@pytest.mark.anyio
async def test_activate_upload_request_does_not_replace_existing_token():
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

        upload_request = UploadRequestRow(
            tenant_id=tenant.id,
            client_id=client.id,
            expires_at=datetime(2026, 12, 1, tzinfo=UTC),
            max_files=3,
        )
        session.add(upload_request)
        await session.commit()

        first_activation = await activate_upload_request(
            session,
            tenant_id=tenant.id,
            upload_request_id=upload_request.id,
        )
        await session.refresh(upload_request)
        first_hash = upload_request.token_hash

        with pytest.raises(UploadRequestActivationConflict):
            await activate_upload_request(
                session,
                tenant_id=tenant.id,
                upload_request_id=upload_request.id,
            )

        await session.refresh(upload_request)
        assert upload_request.token_hash == first_hash
        assert first_hash is not None
        assert upload_token_matches(first_activation.raw_token, first_hash)

    await engine.dispose()


@pytest.mark.anyio
async def test_activate_upload_request_hides_other_tenant_request():
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

        client = ClientRow(
            tenant_id=first_tenant.id,
            name="First Tenant Client",
        )
        session.add(client)
        await session.flush()

        upload_request = UploadRequestRow(
            tenant_id=first_tenant.id,
            client_id=client.id,
            expires_at=datetime(2026, 12, 1, tzinfo=UTC),
            max_files=3,
        )
        session.add(upload_request)
        await session.commit()

        with pytest.raises(UploadRequestNotFound):
            await activate_upload_request(
                session,
                tenant_id=second_tenant.id,
                upload_request_id=upload_request.id,
            )

        await session.refresh(upload_request)
        assert upload_request.status == "draft"
        assert upload_request.token_hash is None

    await engine.dispose()
