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
    DocumentRequirementRow,
    DocumentSubmissionRow,
    TenantRow,
    UploadRequestRow,
)


def enable_sqlite_foreign_keys(engine):
    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, _):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


async def create_requirement(session):
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
        token_hash="a" * 64,
        expires_at=datetime(2026, 12, 1, tzinfo=UTC),
        max_files=3,
    )
    session.add(upload_request)
    await session.flush()

    requirement = DocumentRequirementRow(
        upload_request_id=upload_request.id,
        label="Signed contract",
    )
    session.add(requirement)
    await session.flush()
    return requirement


@pytest.mark.anyio
async def test_submission_preserves_file_metadata_and_pending_scan_default():
    engine = create_database_engine("sqlite+aiosqlite:///:memory:")
    enable_sqlite_foreign_keys(engine)

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    session_factory = create_session_factory(engine)

    async with session_factory() as session:
        requirement = await create_requirement(session)
        session.add(
            DocumentSubmissionRow(
                document_requirement_id=requirement.id,
                storage_key="tenants/1/upload-requests/1/generated-id",
                original_filename="signed-contract.pdf",
                content_type="application/pdf",
                size_bytes=2048,
                sha256="b" * 64,
            )
        )
        await session.commit()

        submission = await session.scalar(select(DocumentSubmissionRow))

        assert submission is not None
        assert submission.original_filename == "signed-contract.pdf"
        assert submission.status == "pending_scan"
        assert submission.size_bytes == 2048

    await engine.dispose()


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("status", "size_bytes"),
    [
        ("uploaded", 2048),
        ("pending_scan", 0),
    ],
)
async def test_submission_rejects_invalid_state_or_empty_file(
    status,
    size_bytes,
):
    engine = create_database_engine("sqlite+aiosqlite:///:memory:")
    enable_sqlite_foreign_keys(engine)

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    session_factory = create_session_factory(engine)

    async with session_factory() as session:
        requirement = await create_requirement(session)
        session.add(
            DocumentSubmissionRow(
                document_requirement_id=requirement.id,
                storage_key="tenants/1/upload-requests/1/generated-id",
                original_filename="signed-contract.pdf",
                content_type="application/pdf",
                size_bytes=size_bytes,
                sha256="b" * 64,
                status=status,
            )
        )

        with pytest.raises(IntegrityError):
            await session.commit()

    await engine.dispose()
