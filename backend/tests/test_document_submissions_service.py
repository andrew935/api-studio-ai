from datetime import UTC, datetime, timedelta
from io import BytesIO

import pytest
from fastapi import UploadFile
from sqlalchemy import event, select
from starlette.datastructures import Headers

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
from backend.app.services.document_submissions import (
    FileStorageUnavailable,
    UploadFileLimitReached,
    create_document_submission,
)


def enable_sqlite_foreign_keys(engine):
    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, _):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


class FakeStorage:
    def __init__(self, *, fail: bool = False):
        self.fail = fail
        self.saved = None

    async def save(self, **kwargs):
        if self.fail:
            raise OSError("S3 unavailable")
        self.saved = {
            "content": kwargs["file_object"].read(),
            "storage_key": kwargs["storage_key"],
            "content_type": kwargs["content_type"],
        }

    async def delete(self, **kwargs):
        return None

    async def close(self):
        return None


def make_pdf() -> UploadFile:
    return UploadFile(
        file=BytesIO(b"%PDF-1.7 synthetic legal document"),
        filename="contract.pdf",
        headers=Headers({"content-type": "application/pdf"}),
    )


async def create_active_request(session, *, max_files: int = 3):
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
        expires_at=datetime.now(UTC) + timedelta(hours=1),
        max_files=max_files,
    )
    session.add(upload_request)
    await session.flush()

    requirement = DocumentRequirementRow(
        upload_request_id=upload_request.id,
        label="Signed contract",
    )
    session.add(requirement)
    await session.commit()
    return upload_request, requirement


@pytest.mark.anyio
async def test_create_submission_reserves_stores_and_enters_pending_scan():
    engine = create_database_engine("sqlite+aiosqlite:///:memory:")
    enable_sqlite_foreign_keys(engine)

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    session_factory = create_session_factory(engine)
    storage = FakeStorage()

    async with session_factory() as session:
        upload_request, requirement = await create_active_request(session)

        created = await create_document_submission(
            session=session,
            storage=storage,
            file=make_pdf(),
            upload_request_id=upload_request.id,
            document_requirement_id=requirement.id,
            max_size_bytes=15 * 1024 * 1024,
        )
        submission = await session.scalar(select(DocumentSubmissionRow))

        assert submission is not None
        assert created.submission_id == submission.id
        assert submission.status == "pending_scan"
        assert storage.saved["content"].startswith(b"%PDF-")
        assert storage.saved["storage_key"] == submission.storage_key

    await engine.dispose()


@pytest.mark.anyio
async def test_create_submission_marks_reservation_failed_when_storage_fails():
    engine = create_database_engine("sqlite+aiosqlite:///:memory:")
    enable_sqlite_foreign_keys(engine)

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    session_factory = create_session_factory(engine)

    async with session_factory() as session:
        upload_request, requirement = await create_active_request(session)

        with pytest.raises(FileStorageUnavailable):
            await create_document_submission(
                session=session,
                storage=FakeStorage(fail=True),
                file=make_pdf(),
                upload_request_id=upload_request.id,
                document_requirement_id=requirement.id,
                max_size_bytes=15 * 1024 * 1024,
            )

        submission = await session.scalar(select(DocumentSubmissionRow))
        assert submission is not None
        assert submission.status == "upload_failed"

    await engine.dispose()


@pytest.mark.anyio
async def test_create_submission_enforces_active_file_limit_before_storage():
    engine = create_database_engine("sqlite+aiosqlite:///:memory:")
    enable_sqlite_foreign_keys(engine)

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    session_factory = create_session_factory(engine)
    storage = FakeStorage()

    async with session_factory() as session:
        upload_request, requirement = await create_active_request(
            session,
            max_files=1,
        )
        session.add(
            DocumentSubmissionRow(
                document_requirement_id=requirement.id,
                storage_key="existing-key",
                original_filename="existing.pdf",
                content_type="application/pdf",
                size_bytes=10,
                sha256="b" * 64,
                status="pending_scan",
            )
        )
        await session.commit()

        with pytest.raises(UploadFileLimitReached):
            await create_document_submission(
                session=session,
                storage=storage,
                file=make_pdf(),
                upload_request_id=upload_request.id,
                document_requirement_id=requirement.id,
                max_size_bytes=15 * 1024 * 1024,
            )

        assert storage.saved is None

    await engine.dispose()
