import pytest

from backend.app.services.circuit_breaker import (
    CircuitBreaker,
    CircuitOpenError,
    CircuitState,
    FailureDisposition,
)


class FakeClock:
    def __init__(self):
        self.value = 0.0

    def __call__(self) -> float:
        return self.value

    def advance(self, seconds: float) -> None:
        self.value += seconds


def classify_timeout(error: Exception) -> FailureDisposition:
    if isinstance(error, TimeoutError):
        return FailureDisposition.COUNT
    return FailureDisposition.IGNORE


@pytest.mark.anyio
async def test_circuit_opens_after_failure_threshold_and_fails_fast():
    calls = 0
    breaker = CircuitBreaker(
        failure_threshold=2,
        recovery_timeout_seconds=30,
        classify_failure=classify_timeout,
    )

    async def failing_operation():
        nonlocal calls
        calls += 1
        raise TimeoutError("dependency timed out")

    for _ in range(2):
        with pytest.raises(TimeoutError):
            await breaker.call(failing_operation)

    with pytest.raises(CircuitOpenError):
        await breaker.call(failing_operation)

    assert calls == 2
    assert breaker.state == CircuitState.OPEN


@pytest.mark.anyio
async def test_half_open_probe_closes_circuit_after_success():
    clock = FakeClock()
    breaker = CircuitBreaker(
        failure_threshold=1,
        recovery_timeout_seconds=30,
        classify_failure=classify_timeout,
        clock=clock,
    )

    async def failing_operation():
        raise TimeoutError("dependency timed out")

    with pytest.raises(TimeoutError):
        await breaker.call(failing_operation)
    clock.advance(30)

    result = await breaker.call(lambda: successful_operation("available"))

    assert result == "available"
    assert breaker.state == CircuitState.CLOSED
    assert breaker.failure_count == 0


@pytest.mark.anyio
async def test_permanent_failure_opens_circuit_immediately():
    breaker = CircuitBreaker(
        failure_threshold=5,
        recovery_timeout_seconds=30,
        classify_failure=lambda _error: FailureDisposition.OPEN,
    )

    async def forbidden_operation():
        raise PermissionError("invalid credentials")

    with pytest.raises(PermissionError):
        await breaker.call(forbidden_operation)

    assert breaker.state == CircuitState.OPEN
    assert breaker.failure_count == 5


async def successful_operation(value: str) -> str:
    return value
