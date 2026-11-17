from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.documents import (
    DocumentSubmissionRow,
    OutboxJobRow,
)
from backend.app.services.document_chunks import (
    replace_document_chunks_in_transaction,
)


PROCESS_DOCUMENT_EVENT = "process_document"


class SubmissionApprovalConflict(RuntimeError):
    """Raised when a submission cannot transition to approved."""


class JobCompletionConflict(RuntimeError):
    """Raised when a job is not processing the expected submission."""


@dataclass(frozen=True)
class EnqueuedDocumentProcessing:
    submission_id: int
    outbox_job_id: int
    idempotency_key: str


@dataclass(frozen=True)
class ClaimedOutboxJob:
    job_id: int
    event_type: str
    aggregate_id: int
    idempotency_key: str
    payload: dict[str, object]
    attempt_count: int


@dataclass(frozen=True)
class RecoveredJobs:
    rescheduled: int
    failed: int


def calculate_retry_delay(
    attempt_count: int,
    *,
    base_seconds: int = 60,
    max_seconds: int = 3600,
) -> timedelta:
    if attempt_count < 1:
        raise ValueError("attempt_count must be at least 1")

    delay_seconds = min(
        base_seconds * (2 ** (attempt_count - 1)),
        max_seconds,
    )
    return timedelta(seconds=delay_seconds)


async def recover_stale_jobs(
    session: AsyncSession,
    *,
    stale_before: datetime,
    now: datetime | None = None,
    max_attempts: int = 5,
    batch_size: int = 100,
) -> RecoveredJobs:
    if max_attempts < 1:
        raise ValueError("max_attempts must be at least 1")
    if batch_size < 1:
        raise ValueError("batch_size must be at least 1")

    recovered_at = now or datetime.now(UTC)

    try:
        jobs = list(
            (
                await session.scalars(
                    select(OutboxJobRow)
                    .where(
                        OutboxJobRow.status == "processing",
                        OutboxJobRow.locked_at < stale_before,
                    )
                    .order_by(OutboxJobRow.id)
                    .limit(batch_size)
                    .with_for_update(skip_locked=True)
                )
            ).all()
        )
        rescheduled = 0
        failed = 0

        for job in jobs:
            job.locked_at = None
            if job.attempt_count >= max_attempts:
                job.status = "failed"
                job.last_error = "Maximum processing attempts exceeded"
                failed += 1
            else:
                job.status = "pending"
                job.available_at = recovered_at + calculate_retry_delay(
                    job.attempt_count
                )
                job.last_error = "Worker lease expired"
                rescheduled += 1

        await session.commit()
        return RecoveredJobs(rescheduled=rescheduled, failed=failed)
    except Exception:
        await session.rollback()
        raise


async def complete_document_processing(
    session: AsyncSession,
    *,
    job_id: int,
    submission_id: int,
    chunks: list[str],
    now: datetime | None = None,
) -> int:
    completed_at = now or datetime.now(UTC)

    try:
        job = await session.scalar(
            select(OutboxJobRow)
            .where(
                OutboxJobRow.id == job_id,
                OutboxJobRow.status == "processing",
                OutboxJobRow.event_type == PROCESS_DOCUMENT_EVENT,
                OutboxJobRow.aggregate_id == submission_id,
            )
            .with_for_update()
        )
        if job is None:
            raise JobCompletionConflict(
                "Job is not processing this submission"
            )

        chunk_count = await replace_document_chunks_in_transaction(
            session,
            document_submission_id=submission_id,
            chunks=chunks,
        )
        job.status = "completed"
        job.completed_at = completed_at
        job.locked_at = None
        job.last_error = None
        await session.commit()
        return chunk_count
    except Exception:
        await session.rollback()
        raise


async def claim_next_job(
    session: AsyncSession,
    *,
    now: datetime | None = None,
) -> ClaimedOutboxJob | None:
    claimed_at = now or datetime.now(UTC)

    try:
        job = await session.scalar(
            select(OutboxJobRow)
            .where(
                OutboxJobRow.status == "pending",
                OutboxJobRow.available_at <= claimed_at,
            )
            .order_by(OutboxJobRow.id)
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        if job is None:
            await session.commit()
            return None

        job.status = "processing"
        job.attempt_count += 1
        job.locked_at = claimed_at
        await session.flush()
        claimed = ClaimedOutboxJob(
            job_id=job.id,
            event_type=job.event_type,
            aggregate_id=job.aggregate_id,
            idempotency_key=job.idempotency_key,
            payload=dict(job.payload),
            attempt_count=job.attempt_count,
        )
        await session.commit()
        return claimed
    except Exception:
        await session.rollback()
        raise


async def approve_submission_and_enqueue(
    session: AsyncSession,
    *,
    submission_id: int,
) -> EnqueuedDocumentProcessing:
    idempotency_key = f"{PROCESS_DOCUMENT_EVENT}:{submission_id}"

    try:
        result = await session.execute(
            update(DocumentSubmissionRow)
            .where(
                DocumentSubmissionRow.id == submission_id,
                DocumentSubmissionRow.status == "pending_review",
            )
            .values(status="approved")
            .returning(DocumentSubmissionRow.id)
        )
        approved_id = result.scalar_one_or_none()

        if approved_id is None:
            existing_job = await session.scalar(
                select(OutboxJobRow).where(
                    OutboxJobRow.idempotency_key == idempotency_key
                )
            )
            if existing_job is None:
                raise SubmissionApprovalConflict(
                    "Submission is not pending review"
                )

            await session.commit()
            return EnqueuedDocumentProcessing(
                submission_id=submission_id,
                outbox_job_id=existing_job.id,
                idempotency_key=existing_job.idempotency_key,
            )

        job = OutboxJobRow(
            event_type=PROCESS_DOCUMENT_EVENT,
            aggregate_id=submission_id,
            idempotency_key=idempotency_key,
            payload={"submission_id": submission_id},
            status="pending",
        )
        session.add(job)
        await session.flush()
        job_id = job.id
        await session.commit()
    except Exception:
        await session.rollback()
        raise

    return EnqueuedDocumentProcessing(
        submission_id=submission_id,
        outbox_job_id=job_id,
        idempotency_key=idempotency_key,
    )
