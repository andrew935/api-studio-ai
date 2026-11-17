from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.services.retrieval import (
    format_retrieved_context,
    retrieve_tenant_chunks,
)


async def search_tenant_documents(
    session: AsyncSession,
    *,
    tenant_id: int,
    query: str,
    limit: int = 3,
) -> dict[str, object]:
    results = await retrieve_tenant_chunks(
        session=session,
        tenant_id=tenant_id,
        query=query,
        limit=limit,
    )
    return {
        "context": format_retrieved_context(results),
        "sources": [
            {
                "chunk_id": chunk.chunk_id,
                "document_submission_id": chunk.document_submission_id,
                "position": chunk.position,
            }
            for _score, chunk in results
        ],
    }
