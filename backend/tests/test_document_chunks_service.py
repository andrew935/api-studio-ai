from datetime import UTC, datetime

import pytest
from sqlalchemy import event, select

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
from backend.app.services.document_chunks import (
    DocumentNotReady,
    InvalidDocumentChunks,
    replace_document_chunks,
)


def enable_sqlite_foreign_keys(engine):
    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, _):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


async def create_submission(
    session,
    *,
    status: str = "approved",
) -> DocumentSubmissionRow:
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
        token_hash="e" * 64,
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
        storage_key=f"synthetic/{status}",
        original_filename="synthetic.pdf",
        content_type="application/pdf",
        size_bytes=100,
        sha256="f" * 64,
        status=status,
    )
    session.add(submission)
    await session.commit()
    return submission


@pytest.fixture
async def chunk_session():
    engine = create_database_engine("sqlite+aiosqlite:///:memory:")
    enable_sqlite_foreign_keys(engine)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = create_session_factory(engine)

    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest.mark.anyio
async def test_replace_document_chunks_is_idempotent(chunk_session):
    submission = await create_submission(chunk_session)

    first_count = await replace_document_chunks(
        chunk_session,
        document_submission_id=submission.id,
        chunks=["first version", "second section"],
    )
    second_count = await replace_document_chunks(
        chunk_session,
        document_submission_id=submission.id,
        chunks=["updated first", "updated second"],
    )

    stored = list(
        (
            await chunk_session.scalars(
                select(DocumentChunkRow)
                .where(
                    DocumentChunkRow.document_submission_id == submission.id
                )
                .order_by(DocumentChunkRow.position)
            )
        ).all()
    )
    assert first_count == 2
    assert second_count == 2
    assert [(row.position, row.content) for row in stored] == [
        (0, "updated first"),
        (1, "updated second"),
    ]


@pytest.mark.anyio
async def test_replace_document_chunks_requires_approved_submission(
    chunk_session,
):
    submission = await create_submission(chunk_session, status="pending_scan")

    with pytest.raises(DocumentNotReady):
        await replace_document_chunks(
            chunk_session,
            document_submission_id=submission.id,
            chunks=["must not be stored"],
        )

    stored = await chunk_session.scalar(select(DocumentChunkRow.id))
    assert stored is None


@pytest.mark.anyio
@pytest.mark.parametrize("chunks", [[], ["   "]])
async def test_replace_document_chunks_rejects_invalid_chunks(
    chunk_session,
    chunks,
):
    submission = await create_submission(chunk_session)

    with pytest.raises(InvalidDocumentChunks):
        await replace_document_chunks(
            chunk_session,
            document_submission_id=submission.id,
            chunks=chunks,
        )
