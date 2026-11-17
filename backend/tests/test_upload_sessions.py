from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import event

from backend.app.config import Settings
from backend.app.db.base import Base
from backend.app.db.session import (
    create_database_engine,
    create_session_factory,
)
from backend.app.models.documents import ClientRow, TenantRow, UploadRequestRow
from backend.app.services.upload_sessions import (
    InvalidUploadSession,
    UploadLinkUnavailable,
    ValidatedUploadLink,
    create_upload_session,
    decode_upload_session,
    validate_upload_link,
)
from backend.app.services.upload_tokens import hash_upload_token


def make_settings() -> Settings:
    return Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        public_base_url="https://documents.example.com",
        jwt_secret_key="test-secret-key-with-at-least-32-characters",
        jwt_issuer="api-studio-ai-tests",
        jwt_audience="api-studio-ai-test-api",
        access_token_expire_minutes=30,
    )


def enable_sqlite_foreign_keys(engine):
    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, _):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def test_upload_session_never_outlives_upload_link():
    settings = make_settings()
    now = datetime.now(UTC)
    upload_link = ValidatedUploadLink(
        upload_request_id=42,
        expires_at=now + timedelta(minutes=10),
    )

    created = create_upload_session(upload_link, settings, now=now)

    assert created.expires_at == upload_link.expires_at
    assert decode_upload_session(created.token, settings) == 42


def test_access_token_cannot_be_used_as_upload_session():
    from backend.app.services.security import create_access_token

    settings = make_settings()
    access_token = create_access_token(17, settings)

    with pytest.raises(InvalidUploadSession):
        decode_upload_session(access_token, settings)


@pytest.mark.anyio
async def test_validate_upload_link_requires_hash_active_status_and_expiration():
    engine = create_database_engine("sqlite+aiosqlite:///:memory:")
    enable_sqlite_foreign_keys(engine)

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    session_factory = create_session_factory(engine)
    now = datetime.now(UTC)

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
            status="active",
            token_hash=hash_upload_token("valid-token"),
            expires_at=now + timedelta(hours=1),
            max_files=3,
        )
        session.add(upload_request)
        await session.commit()

        validated = await validate_upload_link(
            session,
            "valid-token",
            now=now,
        )
        assert validated.upload_request_id == upload_request.id

        for raw_token, status, expires_at in [
            ("wrong-token", "active", now + timedelta(hours=1)),
            ("valid-token", "revoked", now + timedelta(hours=1)),
            ("valid-token", "active", now - timedelta(seconds=1)),
        ]:
            upload_request.status = status
            upload_request.expires_at = expires_at
            await session.commit()

            with pytest.raises(UploadLinkUnavailable):
                await validate_upload_link(session, raw_token, now=now)

        await session.rollback()

    await engine.dispose()
