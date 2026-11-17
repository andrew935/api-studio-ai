import asyncio
from types import SimpleNamespace

import pytest
from redis.exceptions import ConnectionError

from backend.app.services.rate_limiter import (
    RateLimitDecision,
    RateLimiterUnavailable,
    RedisRateLimiter,
    check_login_limits,
    create_email_identifier,
    create_ip_identifier,
)


class FakeRedis:
    def __init__(self, result=None, error=None):
        self.result = result or [1, 300]
        self.error = error
        self.calls = []
        self.closed = False

    async def eval(self, *args):
        self.calls.append(args)
        if self.error is not None:
            raise self.error
        return self.result

    async def aclose(self):
        self.closed = True


class FakeLimiter:
    def __init__(self, decisions):
        self.decisions = iter(decisions)
        self.calls = []

    async def hit(self, **kwargs):
        self.calls.append(kwargs)
        return next(self.decisions)

    async def close(self):
        pass


def test_email_identifier_is_normalized_deterministic_and_not_plaintext():
    secret = "test-rate-limit-secret-with-32-characters"

    first = create_email_identifier(" Andrew@Example.com ", secret)
    second = create_email_identifier("andrew@example.com", secret)

    assert first == second
    assert "andrew" not in first
    assert len(first) == 64


def test_ip_identifier_does_not_store_plain_ip():
    identifier = create_ip_identifier(
        "192.0.2.10",
        "test-rate-limit-secret-with-32-characters",
    )

    assert "192.0.2.10" not in identifier
    assert len(identifier) == 64


def test_redis_rate_limiter_uses_atomic_increment_with_expiry():
    client = FakeRedis(result=[6, 42])
    limiter = RedisRateLimiter(client)

    decision = asyncio.run(
        limiter.hit(
            key="login:pair:test",
            limit=5,
            window_seconds=300,
        )
    )

    assert decision == RateLimitDecision(False, 42)
    script, key_count, key, window = client.calls[0]
    assert "INCR" in script
    assert "EXPIRE" in script
    assert key_count == 1
    assert key == "login:pair:test"
    assert window == 300


def test_redis_error_becomes_safe_unavailable_error():
    limiter = RedisRateLimiter(
        FakeRedis(error=ConnectionError("private Redis address"))
    )

    with pytest.raises(RateLimiterUnavailable):
        asyncio.run(
            limiter.hit(
                key="login:ip:test",
                limit=100,
                window_seconds=900,
            )
        )


def test_login_limits_return_longest_retry_after():
    limiter = FakeLimiter(
        [
            RateLimitDecision(True, 0),
            RateLimitDecision(False, 60),
            RateLimitDecision(False, 20),
        ]
    )
    settings = SimpleNamespace(
        login_ip_limit=100,
        login_ip_window_seconds=900,
        login_email_limit=10,
        login_email_window_seconds=900,
        login_pair_limit=5,
        login_pair_window_seconds=300,
    )

    decision = asyncio.run(
        check_login_limits(
            rate_limiter=limiter,
            client_ip_identifier="hashed-ip",
            email_identifier="hashed-email",
            settings=settings,
        )
    )

    assert decision == RateLimitDecision(False, 60)
    assert len(limiter.calls) == 3
