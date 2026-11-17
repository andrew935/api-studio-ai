from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.documents import (
    DocumentChunkRow,
    DocumentSubmissionRow,
)


class DocumentNotReady(LookupError):
    """Raised when a submission is missing or is not approved for processing."""


class InvalidDocumentChunks(ValueError):
    """Raised when extracted document chunks are empty or invalid."""


async def replace_document_chunks(
    session: AsyncSession,
    *,
    document_submission_id: int,
    chunks: list[str],
) -> int:
    try:
        chunk_count = await replace_document_chunks_in_transaction(
            session,
            document_submission_id=document_submission_id,
            chunks=chunks,
        )
        await session.commit()
    except Exception:
        await session.rollback()
        raise

    return chunk_count


async def replace_document_chunks_in_transaction(
    session: AsyncSession,
    *,
    document_submission_id: int,
    chunks: list[str],
) -> int:
    """Replace derived chunks without committing the caller's transaction."""
    if not chunks or any(not content.strip() for content in chunks):
        raise InvalidDocumentChunks("document chunks must not be empty")

    submission_id = await session.scalar(
        select(DocumentSubmissionRow.id)
        .where(
            DocumentSubmissionRow.id == document_submission_id,
            DocumentSubmissionRow.status == "approved",
        )
        .with_for_update()
    )
    if submission_id is None:
        raise DocumentNotReady("document is not ready for processing")

    await session.execute(
        delete(DocumentChunkRow).where(
            DocumentChunkRow.document_submission_id
            == document_submission_id
        )
    )
    session.add_all(
        [
            DocumentChunkRow(
                document_submission_id=document_submission_id,
                position=position,
                content=content,
            )
            for position, content in enumerate(chunks)
        ]
    )
    await session.flush()

    return len(chunks)
