from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from sqlalchemy import event

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
from backend.app.services.document_chunks import replace_document_chunks
from backend.app.services.document_processing import split_into_chunks
from backend.app.services.rag import GeneratedRagAnswer, answer_question_with_rag


class FakeResponses:
    def __init__(self):
        self.request = None

    async def parse(self, **kwargs):
        self.request = kwargs
        return SimpleNamespace(
            output_parsed=GeneratedRagAnswer(
                answer="A party may cancel within 30 days."
            )
        )


class FakeOpenAIClient:
    def __init__(self):
        self.responses = FakeResponses()


def enable_sqlite_foreign_keys(engine):
    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, _):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


async def create_approved_submission(session):
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
        token_hash="9" * 64,
        expires_at=datetime(2026, 12, 1, tzinfo=UTC),
        max_files=3,
    )
    session.add(upload_request)
    await session.flush()
    requirement = DocumentRequirementRow(
        upload_request_id=upload_request.id,
        label="Synthetic agreement",
    )
    session.add(requirement)
    await session.flush()
    submission = DocumentSubmissionRow(
        document_requirement_id=requirement.id,
        storage_key="vertical-slice/synthetic-agreement",
        original_filename="synthetic-agreement.pdf",
        content_type="application/pdf",
        size_bytes=200,
        sha256="8" * 64,
        status="approved",
    )
    session.add(submission)
    await session.commit()
    return tenant, submission


@pytest.mark.anyio
async def test_synthetic_document_to_sourced_rag_answer():
    engine = create_database_engine("sqlite+aiosqlite:///:memory:")
    enable_sqlite_foreign_keys(engine)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = create_session_factory(engine)
    client = FakeOpenAIClient()

    async with session_factory() as session:
        tenant, submission = await create_approved_submission(session)
        text = (
            "The synthetic agreement starts today. Either party "
            "may cancel within 30 days. Payment is due monthly."
        )
        chunks = split_into_chunks(text, max_words=7)
        await replace_document_chunks(
            session,
            document_submission_id=submission.id,
            chunks=chunks,
        )

        result = await answer_question_with_rag(
            "party cancel days",
            tenant_id=tenant.id,
            session=session,
            client=client,
            limit=2,
        )

    assert result.answer == "A party may cancel within 30 days."
    assert result.sources
    assert all(
        source.document_submission_id == submission.id
        for source in result.sources
    )
    assert "cancel within 30 days" in client.responses.request["input"]
    await engine.dispose()
