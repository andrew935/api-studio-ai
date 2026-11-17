from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from backend.app.api.dependencies import get_database_session
from backend.app.api.dependencies import get_file_storage
from backend.app.api.routes.public_uploads import get_upload_request_id
from backend.app.config import Settings, get_settings
from backend.app.main import app
from backend.app.services.upload_sessions import (
    UploadLinkUnavailable,
    ValidatedUploadLink,
)
from backend.app.services.document_submissions import CreatedSubmission


class FakeSession:
    pass


class FakeStorage:
    async def save(self, **kwargs):
        return None

    async def delete(self, **kwargs):
        return None

    async def close(self):
        return None


async def fake_database_session() -> AsyncIterator[FakeSession]:
    yield FakeSession()


def fake_settings() -> Settings:
    return Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        public_base_url="https://documents.example.com",
        jwt_secret_key="test-secret-key-with-at-least-32-characters",
        jwt_issuer="api-studio-ai-tests",
        jwt_audience="api-studio-ai-test-api",
        access_token_expire_minutes=30,
    )


@pytest.fixture
def client():
    app.dependency_overrides[get_database_session] = fake_database_session
    app.dependency_overrides[get_settings] = fake_settings

    try:
        with TestClient(app, base_url="https://testserver") as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()


def test_exchange_upload_link_sets_secure_session_cookie(client, monkeypatch):
    expires_at = datetime.now(UTC) + timedelta(minutes=10)

    async def fake_validate_upload_link(session, raw_token):
        assert raw_token == "raw-link-token"
        return ValidatedUploadLink(
            upload_request_id=42,
            expires_at=expires_at,
        )

    monkeypatch.setattr(
        "backend.app.api.routes.public_uploads.validate_upload_link",
        fake_validate_upload_link,
    )

    response = client.post(
        "/api/v1/public/uploads/session",
        headers={"X-Upload-Link-Token": "raw-link-token"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "ready"
    assert "raw-link-token" not in response.text
    cookie = response.headers["set-cookie"].lower()
    assert "upload_session=" in cookie
    assert "httponly" in cookie
    assert "secure" in cookie
    assert "samesite=strict" in cookie


def test_exchange_upload_link_hides_failure_reason(client, monkeypatch):
    async def reject_upload_link(session, raw_token):
        raise UploadLinkUnavailable("specific internal reason")

    monkeypatch.setattr(
        "backend.app.api.routes.public_uploads.validate_upload_link",
        reject_upload_link,
    )

    response = client.post(
        "/api/v1/public/uploads/session",
        headers={"X-Upload-Link-Token": "invalid-token"},
    )

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Upload link not found or unavailable"
    }


def test_upload_submission_returns_pending_scan_metadata(client, monkeypatch):
    app.dependency_overrides[get_upload_request_id] = lambda: 42
    app.dependency_overrides[get_file_storage] = lambda: FakeStorage()

    async def fake_create_document_submission(**kwargs):
        assert kwargs["upload_request_id"] == 42
        assert kwargs["document_requirement_id"] == 9
        assert kwargs["max_size_bytes"] == 15 * 1024 * 1024
        return CreatedSubmission(
            submission_id=100,
            original_filename="contract.pdf",
            size_bytes=20,
            sha256="a" * 64,
        )

    monkeypatch.setattr(
        "backend.app.api.routes.public_uploads.create_document_submission",
        fake_create_document_submission,
    )

    response = client.post(
        "/api/v1/public/uploads/requirements/9/submissions",
        files={
            "file": (
                "contract.pdf",
                b"%PDF-1.7 synthetic",
                "application/pdf",
            )
        },
    )

    assert response.status_code == 201
    assert response.json() == {
        "submission_id": 100,
        "status": "pending_scan",
        "original_filename": "contract.pdf",
        "size_bytes": 20,
        "sha256": "a" * 64,
    }


def test_upload_submission_requires_session_cookie(client):
    response = client.post(
        "/api/v1/public/uploads/requirements/9/submissions",
        files={
            "file": (
                "contract.pdf",
                b"%PDF-1.7 synthetic",
                "application/pdf",
            )
        },
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Upload session required"}
