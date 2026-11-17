from datetime import UTC, datetime

import pytest
from sqlalchemy import delete, event, func, select
from sqlalchemy.exc import IntegrityError

from backend.app.db.base import Base
from backend.app.db.session import (
    create_database_engine,
    create_session_factory,
)
from backend.app.models.documents import (
    ClientRow,
    DocumentChunkRow,
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


async def create_submission(session) -> DocumentSubmissionRow:
    tenant = TenantRow(name="Synthetic Law Firm")
    session.add(tenant)
    await session.flush()

    client = ClientRow(tenant_id=tenant.id, name="Synthetic Client")
    session.add(client)
    await session.flush()

    upload_request = UploadRequestRow(
        tenant_id=tenant.id,
        client_id=client.id,
        status="active",
        token_hash="c" * 64,
        expires_at=datetime(2026, 12, 1, tzinfo=UTC),
        max_files=3,
    )
    session.add(upload_request)
    await session.flush()

    requirement = DocumentRequirementRow(
        upload_request_id=upload_request.id,
        label="Synthetic contract",
    )
    session.add(requirement)
    await session.flush()

    submission = DocumentSubmissionRow(
        document_requirement_id=requirement.id,
        storage_key="tenants/1/upload-requests/1/synthetic",
        original_filename="synthetic-contract.pdf",
        content_type="application/pdf",
        size_bytes=1024,
        sha256="d" * 64,
        status="approved",
    )
    session.add(submission)
    await session.flush()
    return submission


@pytest.mark.anyio
async def test_document_chunk_preserves_order_and_rejects_duplicate_position():
    engine = create_database_engine("sqlite+aiosqlite:///:memory:")
    enable_sqlite_foreign_keys(engine)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = create_session_factory(engine)

    async with session_factory() as session:
        submission = await create_submission(session)
        session.add_all(
            [
                DocumentChunkRow(
                    document_submission_id=submission.id,
                    position=0,
                    content="First synthetic section",
                ),
                DocumentChunkRow(
                    document_submission_id=submission.id,
                    position=1,
                    content="Second synthetic section",
                ),
            ]
        )
        await session.commit()

        session.add(
            DocumentChunkRow(
                document_submission_id=submission.id,
                position=1,
                content="Duplicate position",
            )
        )
        with pytest.raises(IntegrityError):
            await session.commit()

    await engine.dispose()


@pytest.mark.anyio
async def test_deleting_submission_cascades_to_derived_chunks():
    engine = create_database_engine("sqlite+aiosqlite:///:memory:")
    enable_sqlite_foreign_keys(engine)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = create_session_factory(engine)

    async with session_factory() as session:
        submission = await create_submission(session)
        session.add(
            DocumentChunkRow(
                document_submission_id=submission.id,
                position=0,
                content="Derived content",
            )
        )
        await session.commit()

        await session.execute(
            delete(DocumentSubmissionRow).where(
                DocumentSubmissionRow.id == submission.id
            )
        )
        await session.commit()

        chunk_count = await session.scalar(
            select(func.count(DocumentChunkRow.id))
        )
        assert chunk_count == 0

    await engine.dispose()


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("position", "content"),
    [(-1, "content"), (0, "   ")],
)
async def test_document_chunk_rejects_invalid_position_or_blank_content(
    position,
    content,
):
    engine = create_database_engine("sqlite+aiosqlite:///:memory:")
    enable_sqlite_foreign_keys(engine)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = create_session_factory(engine)

    async with session_factory() as session:
        submission = await create_submission(session)
        session.add(
            DocumentChunkRow(
                document_submission_id=submission.id,
                position=position,
                content=content,
            )
        )
        with pytest.raises(IntegrityError):
            await session.commit()

    await engine.dispose()
