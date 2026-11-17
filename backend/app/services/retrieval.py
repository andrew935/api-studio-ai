from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.documents import (
    DocumentChunkRow,
    DocumentRequirementRow,
    DocumentSubmissionRow,
    UploadRequestRow,
)


@dataclass(frozen=True)
class DocumentChunk:
    chunk_id: int
    tenant_id: int
    document_submission_id: int
    content: str
    position: int


def format_chunk_for_prompt(chunk: DocumentChunk) -> str:
    return (
        f"[chunk_id={chunk.chunk_id}, "
        f"submission_id={chunk.document_submission_id}, "
        f"position={chunk.position}]\n"
        f"{chunk.content}"
    )


def format_retrieved_context(
    results: list[tuple[int, DocumentChunk]],
) -> str:
    formatted_chunks = []

    for _score, chunk in results:
        formatted_chunks.append(format_chunk_for_prompt(chunk))

    return "\n\n".join(formatted_chunks)


def filter_tenant_chunks(
    chunks: list[DocumentChunk],
    tenant_id: int,
) -> list[DocumentChunk]:
    return [chunk for chunk in chunks if chunk.tenant_id == tenant_id]


def chunk_matches_query(chunk: DocumentChunk, query: str) -> bool:
    query_words = query.lower().split()
    normalized_content = chunk.content.lower()
    return any(
        query_word in normalized_content for query_word in query_words
    )


def calculate_chunk_score(chunk: DocumentChunk, query: str) -> int:
    query_words = query.lower().split()
    normalized_content = chunk.content.lower()
    return sum(
        query_word in normalized_content for query_word in query_words
    )


def score_tenant_chunks(
    chunks: list[DocumentChunk],
    tenant_id: int,
    query: str,
    limit: int = 3,
) -> list[tuple[int, DocumentChunk]]:
    if limit < 1:
        raise ValueError("limit must be at least 1")

    scored_chunks: list[tuple[int, DocumentChunk]] = []

    for chunk in chunks:
        if chunk.tenant_id != tenant_id:
            continue

        score = calculate_chunk_score(chunk, query)
        if score > 0:
            scored_chunks.append((score, chunk))

    return sorted(
        scored_chunks,
        key=lambda result: result[0],
        reverse=True,
    )[:limit]


async def retrieve_tenant_chunks(
    session: AsyncSession,
    *,
    tenant_id: int,
    query: str,
    limit: int = 3,
) -> list[tuple[int, DocumentChunk]]:
    result = await session.execute(
        select(
            DocumentChunkRow.id,
            UploadRequestRow.tenant_id,
            DocumentChunkRow.document_submission_id,
            DocumentChunkRow.content,
            DocumentChunkRow.position,
        )
        .join(
            DocumentSubmissionRow,
            DocumentSubmissionRow.id
            == DocumentChunkRow.document_submission_id,
        )
        .join(
            DocumentRequirementRow,
            DocumentRequirementRow.id
            == DocumentSubmissionRow.document_requirement_id,
        )
        .join(
            UploadRequestRow,
            UploadRequestRow.id
            == DocumentRequirementRow.upload_request_id,
        )
        .where(
            UploadRequestRow.tenant_id == tenant_id,
            DocumentSubmissionRow.status == "approved",
        )
    )
    chunks = [
        DocumentChunk(
            chunk_id=row.id,
            tenant_id=row.tenant_id,
            document_submission_id=row.document_submission_id,
            content=row.content,
            position=row.position,
        )
        for row in result.all()
    ]
    return score_tenant_chunks(
        chunks,
        tenant_id=tenant_id,
        query=query,
        limit=limit,
    )
