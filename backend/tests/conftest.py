import os


os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("PUBLIC_BASE_URL", "http://testserver")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-with-at-least-32-characters")
os.environ.setdefault("JWT_ISSUER", "api-studio-ai-tests")
os.environ.setdefault("JWT_AUDIENCE", "api-studio-ai-test-api")
os.environ.setdefault("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
os.environ.setdefault(
    "RATE_LIMIT_HMAC_KEY",
    "test-rate-limit-hmac-key-with-32-characters",
)
