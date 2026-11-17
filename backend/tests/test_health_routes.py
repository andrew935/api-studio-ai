from collections.abc import AsyncIterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError

from backend.app.api.dependencies import get_database_session
from backend.app.main import app


class FakeSession:
    def __init__(self, error: SQLAlchemyError | None = None):
        self.error = error
        self.statements = []

    async def execute(self, statement):
        self.statements.append(statement)
        if self.error is not None:
            raise self.error


@pytest.fixture
def session():
    return FakeSession()


@pytest.fixture
def client(session):
    async def fake_database_session() -> AsyncIterator[FakeSession]:
        yield session

    app.dependency_overrides[get_database_session] = fake_database_session

    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()


def test_liveness_reports_running_process(client):
    response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readiness_reports_available_database(client, session):
    response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "database": "ok",
    }
    assert len(session.statements) == 1


def test_readiness_returns_503_when_database_is_unavailable(client, session):
    session.error = SQLAlchemyError("internal database details")

    response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json() == {"detail": "Service not ready"}
    assert "internal database details" not in response.text
