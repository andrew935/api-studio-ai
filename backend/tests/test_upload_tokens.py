from backend.app.services.upload_tokens import (
    generate_upload_token,
    hash_upload_token,
    upload_token_matches,
)


def test_generate_upload_token_returns_unique_tokens():
    first_token = generate_upload_token()
    second_token = generate_upload_token()

    assert first_token != second_token
    assert len(first_token) >= 40
    assert len(second_token) >= 40


def test_hash_upload_token_is_deterministic_without_storing_raw_token():
    token = generate_upload_token()

    first_hash = hash_upload_token(token)
    second_hash = hash_upload_token(token)

    assert first_hash == second_hash
    assert first_hash != token
    assert len(first_hash) == 64


def test_upload_token_matches_only_the_original_token():
    token = generate_upload_token()
    token_hash = hash_upload_token(token)

    assert upload_token_matches(token, token_hash) is True
    assert upload_token_matches("wrong-token", token_hash) is False
