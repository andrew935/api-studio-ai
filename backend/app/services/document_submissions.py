from dataclasses import dataclass
from datetime import UTC, datetime

from fastapi import UploadFile
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.documents import (
    DocumentRequirementRow,
    DocumentSubmissionRow,
    UploadRequestRow,
)
from backend.app.services.file_storage import FileStorage, generate_storage_key
from backend.app.services.file_uploads import InspectedUpload, inspect_upload


class PublicUploadUnavailable(LookupError):
    """Raised without exposing which public-upload condition failed."""


class UploadFileLimitReached(RuntimeError):
    """Raised when an upload request has no remaining active file slots."""


class FileStorageUnavailable(RuntimeError):
    """Raised when the configured file storage cannot accept the upload."""


class SubmissionFinalizationConflict(RuntimeError):
    """Raised when a stored object cannot enter pending_scan atomically."""


@dataclass(frozen=True)
class ReservedSubmission:
    submission_id: int
    storage_key: str
    inspected: InspectedUpload


@dataclass(frozen=True)
class CreatedSubmission:
    submission_id: int
    original_filename: str
    size_bytes: int
    sha256: str


async def reserve_submission(
    session: AsyncSession,
    *,
    upload_request_id: int,
    document_requirement_id: int,
    inspected: InspectedUpload,
    now: datetime | None = None,
) -> ReservedSubmission:
    checked_at = now or datetime.now(UTC)

    try:
        result = await session.execute(
            select(
                UploadRequestRow.id,
                UploadRequestRow.tenant_id,
                UploadRequestRow.max_files,
            )
            .join(
                DocumentRequirementRow,
                DocumentRequirementRow.upload_request_id
                == UploadRequestRow.id,
            )
            .where(
                UploadRequestRow.id == upload_request_id,
                UploadRequestRow.status == "active",
                UploadRequestRow.expires_at > checked_at,
                DocumentRequirementRow.id == document_requirement_id,
            )
            .with_for_update()
        )
        upload_request = result.one_or_none()
        if upload_request is None:
            raise PublicUploadUnavailable(
                "Upload link not found or unavailable"
            )

        active_submission_count = await session.scalar(
            select(func.count(DocumentSubmissionRow.id))
            .join(
                DocumentRequirementRow,
                DocumentRequirementRow.id
                == DocumentSubmissionRow.document_requirement_id,
            )
            .where(
                DocumentRequirementRow.upload_request_id
                == upload_request_id,
                DocumentSubmissionRow.status.notin_(
                    ["rejected", "upload_failed"]
                ),
            )
        )
        if (active_submission_count or 0) >= upload_request.max_files:
            raise UploadFileLimitReached("Upload file limit reached")

        storage_key = generate_storage_key(
            tenant_id=upload_request.tenant_id,
            upload_request_id=upload_request_id,
        )
        submission = DocumentSubmissionRow(
            document_requirement_id=document_requirement_id,
            storage_key=storage_key,
            original_filename=inspected.original_filename,
            content_type=inspected.content_type,
            size_bytes=inspected.size_bytes,
            sha256=inspected.sha256,
            status="uploading",
        )
        session.add(submission)
        await session.flush()
        submission_id = submission.id
        await session.commit()
    except Exception:
        await session.rollback()
        raise

    return ReservedSubmission(
        submission_id=submission_id,
        storage_key=storage_key,
        inspected=inspected,
    )


async def set_submission_status(
    session: AsyncSession,
    *,
    submission_id: int,
    current_status: str,
    target_status: str,
) -> bool:
    result = await session.execute(
        update(DocumentSubmissionRow)
        .where(
            DocumentSubmissionRow.id == submission_id,
            DocumentSubmissionRow.status == current_status,
        )
        .values(status=target_status)
        .returning(DocumentSubmissionRow.id)
    )
    changed = result.scalar_one_or_none() is not None
    await session.commit()
    return changed


async def create_document_submission(
    session: AsyncSession,
    storage: FileStorage,
    file: UploadFile,
    *,
    upload_request_id: int,
    document_requirement_id: int,
    max_size_bytes: int,
) -> CreatedSubmission:
    inspected = await inspect_upload(file, max_size_bytes=max_size_bytes)
    reserved = await reserve_submission(
        session,
        upload_request_id=upload_request_id,
        document_requirement_id=document_requirement_id,
        inspected=inspected,
    )

    try:
        await storage.save(
            file_object=file.file,
            storage_key=reserved.storage_key,
            content_type=inspected.content_type,
        )
    except Exception as error:
        try:
            await set_submission_status(
                session,
                submission_id=reserved.submission_id,
                current_status="uploading",
                target_status="upload_failed",
            )
        except Exception:
            await session.rollback()
        raise FileStorageUnavailable("File storage is unavailable") from error

    try:
        changed = await set_submission_status(
            session,
            submission_id=reserved.submission_id,
            current_status="uploading",
            target_status="pending_scan",
        )
    except Exception:
        await session.rollback()
        raise

    if not changed:
        raise SubmissionFinalizationConflict(
            "Submission could not enter pending_scan"
        )

    return CreatedSubmission(
        submission_id=reserved.submission_id,
        original_filename=inspected.original_filename,
        size_bytes=inspected.size_bytes,
        sha256=inspected.sha256,
    )
