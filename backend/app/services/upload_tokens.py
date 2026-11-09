import hashlib
import hmac
import secrets


TOKEN_BYTES = 32


def generate_upload_token() -> str:
    """Generate a high-entropy token suitable for a public upload URL."""

    return secrets.token_urlsafe(TOKEN_BYTES)


def hash_upload_token(token: str) -> str:
    """Hash a high-entropy token before database storage."""

    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def upload_token_matches(token: str, expected_hash: str) -> bool:
    """Compare a presented upload token with the stored hash."""

    actual_hash = hash_upload_token(token)
    return hmac.compare_digest(actual_hash, expected_hash)
