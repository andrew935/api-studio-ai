import pytest

from backend.app.services.retrieval import (
    DocumentChunk,
    calculate_chunk_score,
    chunk_matches_query,
    filter_tenant_chunks,
    format_chunk_for_prompt,
    format_retrieved_context,
    score_tenant_chunks,
)


def make_chunk(
    chunk_id: int,
    tenant_id: int,
    content: str,
) -> DocumentChunk:
    return DocumentChunk(
        chunk_id=chunk_id,
        tenant_id=tenant_id,
        document_submission_id=100 + chunk_id,
        content=content,
        position=0,
    )


def test_filter_tenant_chunks_excludes_other_tenants_without_mutation():
    chunks = [
        make_chunk(1, 10, "Tenant ten contract"),
        make_chunk(2, 20, "Tenant twenty private contract"),
    ]

    filtered = filter_tenant_chunks(chunks, tenant_id=10)

    assert [chunk.chunk_id for chunk in filtered] == [1]
    assert len(chunks) == 2


def test_format_chunk_for_prompt_includes_real_source_metadata():
    chunk = DocumentChunk(
        chunk_id=15,
        tenant_id=10,
        document_submission_id=7,
        content="The contract may be cancelled within 30 days.",
        position=2,
    )

    assert format_chunk_for_prompt(chunk) == (
        "[chunk_id=15, submission_id=7, position=2]\n"
        "The contract may be cancelled within 30 days."
    )


def test_format_retrieved_context_separates_chunks():
    first = make_chunk(1, 10, "First source")
    second = make_chunk(2, 10, "Second source")

    context = format_retrieved_context([(2, first), (1, second)])

    assert context == (
        "[chunk_id=1, submission_id=101, position=0]\n"
        "First source\n\n"
        "[chunk_id=2, submission_id=102, position=0]\n"
        "Second source"
    )


def test_format_retrieved_context_returns_empty_string_without_results():
    assert format_retrieved_context([]) == ""


def test_chunk_match_and_score_are_case_insensitive():
    chunk = make_chunk(1, 10, "The CONTRACT was signed yesterday")

    assert chunk_matches_query(chunk, "signed invoice") is True
    assert calculate_chunk_score(chunk, "SIGNED contract invoice") == 2


def test_score_tenant_chunks_ranks_limits_and_excludes_other_tenants():
    chunks = [
        make_chunk(1, 10, "signed contract"),
        make_chunk(2, 10, "signed contract invoice"),
        make_chunk(3, 10, "invoice only"),
        make_chunk(4, 20, "signed contract invoice private"),
    ]

    results = score_tenant_chunks(
        chunks,
        tenant_id=10,
        query="signed contract invoice",
        limit=2,
    )

    assert [(score, chunk.chunk_id) for score, chunk in results] == [
        (3, 2),
        (2, 1),
    ]


def test_score_tenant_chunks_omits_zero_score_chunks():
    results = score_tenant_chunks(
        [make_chunk(1, 10, "power of attorney")],
        tenant_id=10,
        query="invoice",
    )

    assert results == []


def test_score_tenant_chunks_rejects_non_positive_limit():
    with pytest.raises(ValueError, match="limit must be at least 1"):
        score_tenant_chunks([], tenant_id=10, query="contract", limit=0)
