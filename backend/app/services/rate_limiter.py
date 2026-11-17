import asyncio
import hashlib
import hmac
from dataclasses import dataclass
from typing import Protocol

from redis.asyncio import Redis
from redis.exceptions import RedisError

from backend.app.config import Settings


INCREMENT_WITH_EXPIRY = """
local current = redis.call('INCR', KEYS[1])
if current == 1 then
    redis.call('EXPIRE', KEYS[1], ARGV[1])
end
local ttl = redis.call('TTL', KEYS[1])
return {current, ttl}
"""


class RateLimiterUnavailable(RuntimeError):
    """Raised when a limit cannot be checked safely."""


@dataclass(frozen=True)
class RateLimitDecision:
    allowed: bool
    retry_after_seconds: int


class RateLimiter(Protocol):
    async def hit(
        self,
        *,
        key: str,
        limit: int,
        window_seconds: int,
    ) -> RateLimitDecision: ...

    async def close(self) -> None: ...


class RedisRateLimiter:
    def __init__(self, client: Redis):
        self._client = client

    async def hit(
        self,
        *,
        key: str,
        limit: int,
        window_seconds: int,
    ) -> RateLimitDecision:
        try:
            current, ttl = await self._client.eval(
                INCREMENT_WITH_EXPIRY,
                1,
                key,
                window_seconds,
            )
        except RedisError as exc:
            raise RateLimiterUnavailable("Rate limiter unavailable") from exc

        retry_after = max(int(ttl), 1)
        return RateLimitDecision(
            allowed=int(current) <= limit,
            retry_after_seconds=retry_after,
        )

    async def close(self) -> None:
        await self._client.aclose()


def create_rate_limiter(settings: Settings) -> RedisRateLimiter:
    client = Redis.from_url(
        settings.redis_url,
        decode_responses=True,
        socket_connect_timeout=2,
        socket_timeout=2,
    )
    return RedisRateLimiter(client)


def create_email_identifier(email: str, secret: str) -> str:
    normalized_email = email.strip().lower()
    return create_hmac_identifier(normalized_email, secret)


def create_ip_identifier(client_ip: str, secret: str) -> str:
    return create_hmac_identifier(client_ip.strip(), secret)


def create_hmac_identifier(value: str, secret: str) -> str:
    return hmac.new(
        secret.encode(),
        value.encode(),
        hashlib.sha256,
    ).hexdigest()


async def check_login_limits(
    *,
    rate_limiter: RateLimiter,
    client_ip_identifier: str,
    email_identifier: str,
    settings: Settings,
) -> RateLimitDecision:
    checks = await asyncio.gather(
        rate_limiter.hit(
            key=f"login:ip:{client_ip_identifier}",
            limit=settings.login_ip_limit,
            window_seconds=settings.login_ip_window_seconds,
        ),
        rate_limiter.hit(
            key=f"login:email:{email_identifier}",
            limit=settings.login_email_limit,
            window_seconds=settings.login_email_window_seconds,
        ),
        rate_limiter.hit(
            key=f"login:pair:{client_ip_identifier}:{email_identifier}",
            limit=settings.login_pair_limit,
            window_seconds=settings.login_pair_window_seconds,
        ),
    )

    blocked_retries = [
        decision.retry_after_seconds
        for decision in checks
        if not decision.allowed
    ]
    if blocked_retries:
        return RateLimitDecision(
            allowed=False,
            retry_after_seconds=max(blocked_retries),
        )

    return RateLimitDecision(allowed=True, retry_after_seconds=0)
