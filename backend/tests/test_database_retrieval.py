from datetime import UTC, datetime

import pytest
from sqlalchemy import event

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
from backend.app.services.retrieval import retrieve_tenant_chunks


def enable_sqlite_foreign_keys(engine):
    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, _):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


async def add_document(
    session,
    *,
    tenant_name: str,
    token_character: str,
    chunk_contents: list[str],
) -> tuple[int, list[int]]:
    tenant = TenantRow(name=tenant_name)
    session.add(tenant)
    await session.flush()
    client = ClientRow(tenant_id=tenant.id, name=f"{tenant_name} Client")
    session.add(client)
    await session.flush()
    upload_request = UploadRequestRow(
        tenant_id=tenant.id,
        client_id=client.id,
        status="active",
        token_hash=token_character * 64,
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
        storage_key=f"retrieval/{tenant.id}",
        original_filename="contract.pdf",
        content_type="application/pdf",
        size_bytes=100,
        sha256=token_character * 64,
        status="approved",
    )
    session.add(submission)
    await session.flush()
    chunks = [
        DocumentChunkRow(
            document_submission_id=submission.id,
            position=position,
            content=content,
        )
        for position, content in enumerate(chunk_contents)
    ]
    session.add_all(chunks)
    await session.commit()
    return tenant.id, [chunk.id for chunk in chunks]


@pytest.mark.anyio
async def test_retrieve_tenant_chunks_filters_before_ranking():
    engine = create_database_engine("sqlite+aiosqlite:///:memory:")
    enable_sqlite_foreign_keys(engine)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = create_session_factory(engine)

    async with session_factory() as session:
        tenant_id, tenant_chunk_ids = await add_document(
            session,
            tenant_name="Allowed Law Firm",
            token_character="a",
            chunk_contents=[
                "signed contract",
                "invoice only",
            ],
        )
        _, other_chunk_ids = await add_document(
            session,
            tenant_name="Private Other Firm",
            token_character="b",
            chunk_contents=["signed contract invoice private"],
        )

        results = await retrieve_tenant_chunks(
            session,
            tenant_id=tenant_id,
            query="signed contract invoice",
            limit=3,
        )

    result_ids = [chunk.chunk_id for _, chunk in results]
    assert result_ids == tenant_chunk_ids
    assert not set(result_ids).intersection(other_chunk_ids)
    assert [score for score, _ in results] == [2, 1]
    await engine.dispose()
