import pytest

from backend.app.services.document_processing import split_into_chunks


def test_split_into_chunks_preserves_word_order_and_size_limit():
    chunks = split_into_chunks(
        "one two three four five six seven",
        max_words=3,
    )

    assert chunks == [
        "one two three",
        "four five six",
        "seven",
    ]


def test_split_into_chunks_normalizes_whitespace():
    chunks = split_into_chunks(
        "first\n\nsecond\tthird    fourth",
        max_words=2,
    )

    assert chunks == ["first second", "third fourth"]


def test_split_into_chunks_returns_empty_list_for_blank_text():
    assert split_into_chunks("   \n\t", max_words=100) == []


@pytest.mark.parametrize("max_words", [0, -1])
def test_split_into_chunks_rejects_non_positive_size(max_words):
    with pytest.raises(ValueError, match="max_words must be at least 1"):
        split_into_chunks("synthetic contract", max_words=max_words)
