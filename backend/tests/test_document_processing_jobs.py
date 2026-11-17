from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import event, func, select
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
    OutboxJobRow,
    TenantRow,
    UploadRequestRow,
)
from backend.app.services.document_processing_jobs import (
    JobCompletionConflict,
    SubmissionApprovalConflict,
    approve_submission_and_enqueue,
    calculate_retry_delay,
    claim_next_job,
    complete_document_processing,
    recover_stale_jobs,
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
    status: str = "pending_review",
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
        token_hash="a" * 64,
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
        original_filename="contract.pdf",
        content_type="application/pdf",
        size_bytes=100,
        sha256="b" * 64,
        status=status,
    )
    session.add(submission)
    await session.commit()
    return submission


@pytest.fixture
async def job_session():
    engine = create_database_engine("sqlite+aiosqlite:///:memory:")
    enable_sqlite_foreign_keys(engine)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = create_session_factory(engine)

    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest.mark.anyio
async def test_approval_and_outbox_job_commit_together(job_session):
    submission = await create_submission(job_session)

    enqueued = await approve_submission_and_enqueue(
        job_session,
        submission_id=submission.id,
    )

    await job_session.refresh(submission)
    job = await job_session.get(OutboxJobRow, enqueued.outbox_job_id)
    assert submission.status == "approved"
    assert job is not None
    assert job.status == "pending"
    assert job.payload == {"submission_id": submission.id}
    assert job.idempotency_key == f"process_document:{submission.id}"


@pytest.mark.anyio
async def test_approval_retry_returns_same_outbox_job(job_session):
    submission = await create_submission(job_session)

    first = await approve_submission_and_enqueue(
        job_session,
        submission_id=submission.id,
    )
    second = await approve_submission_and_enqueue(
        job_session,
        submission_id=submission.id,
    )

    job_count = await job_session.scalar(select(func.count(OutboxJobRow.id)))
    assert second == first
    assert job_count == 1


@pytest.mark.anyio
async def test_non_pending_submission_cannot_create_job(job_session):
    submission = await create_submission(job_session, status="rejected")

    with pytest.raises(SubmissionApprovalConflict):
        await approve_submission_and_enqueue(
            job_session,
            submission_id=submission.id,
        )

    job_count = await job_session.scalar(select(func.count(OutboxJobRow.id)))
    assert job_count == 0


@pytest.mark.anyio
async def test_duplicate_job_rolls_back_submission_approval(job_session):
    submission = await create_submission(job_session)
    submission_id = submission.id
    job_session.add(
        OutboxJobRow(
            event_type="process_document",
            aggregate_id=submission_id,
            idempotency_key=f"process_document:{submission_id}",
            payload={"submission_id": submission_id},
        )
    )
    await job_session.commit()

    with pytest.raises(IntegrityError):
        await approve_submission_and_enqueue(
            job_session,
            submission_id=submission_id,
        )

    stored_status = await job_session.scalar(
        select(DocumentSubmissionRow.status).where(
            DocumentSubmissionRow.id == submission_id
        )
    )
    assert stored_status == "pending_review"


@pytest.mark.anyio
async def test_claim_next_job_marks_oldest_available_job_processing(
    job_session,
):
    now = datetime(2026, 11, 16, 10, 0, tzinfo=UTC)
    job_session.add_all(
        [
            OutboxJobRow(
                event_type="process_document",
                aggregate_id=10,
                idempotency_key="process_document:10",
                payload={"submission_id": 10},
                available_at=now - timedelta(minutes=1),
            ),
            OutboxJobRow(
                event_type="process_document",
                aggregate_id=11,
                idempotency_key="process_document:11",
                payload={"submission_id": 11},
                available_at=now - timedelta(minutes=1),
            ),
            OutboxJobRow(
                event_type="process_document",
                aggregate_id=12,
                idempotency_key="process_document:12",
                payload={"submission_id": 12},
                available_at=now + timedelta(minutes=5),
            ),
        ]
    )
    await job_session.commit()

    first = await claim_next_job(job_session, now=now)
    second = await claim_next_job(job_session, now=now)
    unavailable = await claim_next_job(job_session, now=now)

    assert first is not None
    assert second is not None
    assert first.aggregate_id == 10
    assert second.aggregate_id == 11
    assert first.attempt_count == 1
    assert unavailable is None

    stored_first = await job_session.get(OutboxJobRow, first.job_id)
    assert stored_first is not None
    assert stored_first.status == "processing"
    assert stored_first.locked_at is not None
    assert stored_first.locked_at.replace(tzinfo=UTC) == now


@pytest.mark.parametrize(
    ("attempt_count", "expected_minutes"),
    [(1, 1), (2, 2), (3, 4), (4, 8)],
)
def test_retry_delay_uses_exponential_backoff(
    attempt_count,
    expected_minutes,
):
    assert calculate_retry_delay(attempt_count) == timedelta(
        minutes=expected_minutes
    )


@pytest.mark.anyio
async def test_recover_stale_job_reschedules_with_backoff(job_session):
    now = datetime(2026, 11, 16, 12, 0, tzinfo=UTC)
    job = OutboxJobRow(
        event_type="process_document",
        aggregate_id=20,
        idempotency_key="process_document:20",
        payload={"submission_id": 20},
        status="processing",
        attempt_count=3,
        locked_at=now - timedelta(minutes=11),
    )
    job_session.add(job)
    await job_session.commit()
    job_id = job.id

    recovered = await recover_stale_jobs(
        job_session,
        stale_before=now - timedelta(minutes=10),
        now=now,
    )

    stored = await job_session.get(OutboxJobRow, job_id)
    assert recovered.rescheduled == 1
    assert recovered.failed == 0
    assert stored is not None
    assert stored.status == "pending"
    assert stored.locked_at is None
    assert stored.available_at.replace(tzinfo=UTC) == now + timedelta(
        minutes=4
    )
    assert stored.last_error == "Worker lease expired"


@pytest.mark.anyio
async def test_recover_stale_job_stops_after_max_attempts(job_session):
    now = datetime(2026, 11, 16, 12, 0, tzinfo=UTC)
    job = OutboxJobRow(
        event_type="process_document",
        aggregate_id=21,
        idempotency_key="process_document:21",
        payload={"submission_id": 21},
        status="processing",
        attempt_count=5,
        locked_at=now - timedelta(minutes=11),
    )
    job_session.add(job)
    await job_session.commit()
    job_id = job.id

    recovered = await recover_stale_jobs(
        job_session,
        stale_before=now - timedelta(minutes=10),
        now=now,
        max_attempts=5,
    )

    stored = await job_session.get(OutboxJobRow, job_id)
    assert recovered.rescheduled == 0
    assert recovered.failed == 1
    assert stored is not None
    assert stored.status == "failed"
    assert stored.locked_at is None
    assert stored.last_error == "Maximum processing attempts exceeded"


@pytest.mark.anyio
async def test_complete_processing_commits_chunks_and_job_together(job_session):
    now = datetime.now(UTC) + timedelta(minutes=1)
    submission = await create_submission(job_session)
    enqueued = await approve_submission_and_enqueue(
        job_session,
        submission_id=submission.id,
    )
    claimed = await claim_next_job(job_session, now=now)
    assert claimed is not None

    chunk_count = await complete_document_processing(
        job_session,
        job_id=enqueued.outbox_job_id,
        submission_id=submission.id,
        chunks=["first section", "second section"],
        now=now,
    )

    job = await job_session.get(OutboxJobRow, enqueued.outbox_job_id)
    stored_chunks = list(
        (
            await job_session.scalars(
                select(DocumentChunkRow)
                .where(
                    DocumentChunkRow.document_submission_id == submission.id
                )
                .order_by(DocumentChunkRow.position)
            )
        ).all()
    )
    assert chunk_count == 2
    assert [chunk.content for chunk in stored_chunks] == [
        "first section",
        "second section",
    ]
    assert job is not None
    assert job.status == "completed"
    assert job.locked_at is None
    assert job.completed_at is not None


@pytest.mark.anyio
async def test_completion_failure_rolls_back_chunks_and_job(job_session):
    now = datetime.now(UTC) + timedelta(minutes=1)
    submission = await create_submission(job_session)
    submission_id = submission.id
    enqueued = await approve_submission_and_enqueue(
        job_session,
        submission_id=submission_id,
    )
    await claim_next_job(job_session, now=now)

    with pytest.raises(ValueError, match="must not be empty"):
        await complete_document_processing(
            job_session,
            job_id=enqueued.outbox_job_id,
            submission_id=submission_id,
            chunks=[],
            now=now,
        )

    job = await job_session.get(OutboxJobRow, enqueued.outbox_job_id)
    chunk_count = await job_session.scalar(
        select(func.count(DocumentChunkRow.id)).where(
            DocumentChunkRow.document_submission_id == submission_id
        )
    )
    assert job is not None
    assert job.status == "processing"
    assert chunk_count == 0


@pytest.mark.anyio
async def test_completion_rejects_wrong_submission(job_session):
    now = datetime.now(UTC) + timedelta(minutes=1)
    submission = await create_submission(job_session)
    enqueued = await approve_submission_and_enqueue(
        job_session,
        submission_id=submission.id,
    )
    await claim_next_job(job_session, now=now)

    with pytest.raises(JobCompletionConflict):
        await complete_document_processing(
            job_session,
            job_id=enqueued.outbox_job_id,
            submission_id=submission.id + 1,
            chunks=["must not be stored"],
            now=now,
        )
