import asyncio
import time
from collections.abc import Awaitable, Callable
from enum import Enum
from typing import TypeVar


ResultT = TypeVar("ResultT")


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class FailureDisposition(str, Enum):
    IGNORE = "ignore"
    COUNT = "count"
    OPEN = "open"


class CircuitOpenError(RuntimeError):
    """Raised when an external dependency is temporarily blocked."""


class CircuitBreaker:
    def __init__(
        self,
        *,
        failure_threshold: int,
        recovery_timeout_seconds: float,
        classify_failure: Callable[[Exception], FailureDisposition],
        clock: Callable[[], float] = time.monotonic,
    ):
        if failure_threshold < 1:
            raise ValueError("failure_threshold must be at least 1")
        if recovery_timeout_seconds <= 0:
            raise ValueError("recovery_timeout_seconds must be positive")

        self.failure_threshold = failure_threshold
        self.recovery_timeout_seconds = recovery_timeout_seconds
        self.classify_failure = classify_failure
        self.clock = clock
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.opened_at: float | None = None
        self._half_open_probe_in_flight = False
        self._lock = asyncio.Lock()

    async def call(
        self,
        operation: Callable[[], Awaitable[ResultT]],
    ) -> ResultT:
        await self._acquire_permission()

        try:
            result = await operation()
        except Exception as error:
            await self._record_failure(error)
            raise

        await self._record_success()
        return result

    async def _acquire_permission(self) -> None:
        async with self._lock:
            if self.state == CircuitState.CLOSED:
                return

            if self.state == CircuitState.HALF_OPEN:
                if self._half_open_probe_in_flight:
                    raise CircuitOpenError("Circuit breaker probe in progress")
                self._half_open_probe_in_flight = True
                return

            assert self.opened_at is not None
            elapsed = self.clock() - self.opened_at
            if elapsed < self.recovery_timeout_seconds:
                raise CircuitOpenError("Circuit breaker is open")

            self.state = CircuitState.HALF_OPEN
            self._half_open_probe_in_flight = True

    async def _record_failure(self, error: Exception) -> None:
        disposition = self.classify_failure(error)

        async with self._lock:
            if disposition == FailureDisposition.IGNORE:
                if self.state == CircuitState.HALF_OPEN:
                    self._open()
                return

            if disposition == FailureDisposition.COUNT:
                self.failure_count += 1
                if (
                    self.state == CircuitState.HALF_OPEN
                    or self.failure_count >= self.failure_threshold
                ):
                    self._open()
                return

            self.failure_count = self.failure_threshold
            self._open()

    async def _record_success(self) -> None:
        async with self._lock:
            self.state = CircuitState.CLOSED
            self.failure_count = 0
            self.opened_at = None
            self._half_open_probe_in_flight = False

    def _open(self) -> None:
        self.state = CircuitState.OPEN
        self.opened_at = self.clock()
        self._half_open_probe_in_flight = False
