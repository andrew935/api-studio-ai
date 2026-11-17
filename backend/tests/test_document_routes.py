from collections.abc import AsyncIterator
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from backend.app.api.dependencies import (
    get_current_tenant_id,
    get_database_session,
)
from backend.app.config import Settings, get_settings
from backend.app.main import app
from backend.app.services.security import create_access_token
from backend.app.services.upload_requests import (
    ActivatedUploadRequest,
    UploadRequestActivationConflict,
    UploadRequestNotFound,
)


class FakeSession:
    async def scalar(self, statement):
        return type(
            "User",
            (),
            {
                "id": 17,
                "tenant_id": 7,
                "role": "staff",
                "is_active": True,
            },
        )()


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
def authenticated_client():
    app.dependency_overrides[get_database_session] = fake_database_session
    app.dependency_overrides[get_settings] = fake_settings
    access_token = create_access_token(
        user_id=17,
        settings=fake_settings(),
    )

    try:
        with TestClient(
            app,
            headers={"Authorization": f"Bearer {access_token}"},
        ) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()


def test_activate_request_returns_public_upload_url(
    authenticated_client,
    monkeypatch,
):
    async def fake_activate_upload_request(**kwargs):
        assert kwargs["tenant_id"] == 7
        assert kwargs["upload_request_id"] == 42
        return ActivatedUploadRequest(
            upload_request_id=42,
            raw_token="raw-secret-token",
            expires_at=datetime(2026, 12, 1, tzinfo=UTC),
        )

    monkeypatch.setattr(
        "backend.app.api.routes.documents.activate_upload_request",
        fake_activate_upload_request,
    )

    response = authenticated_client.post(
        "/api/v1/upload-requests/42/activate"
    )

    assert response.status_code == 200
    assert response.json() == {
        "upload_request_id": 42,
        "status": "active",
        "upload_url": "https://documents.example.com/upload#token=raw-secret-token",
        "expires_at": "2026-12-01T00:00:00Z",
    }


@pytest.mark.parametrize(
    ("error", "expected_status", "expected_detail"),
    [
        (
            UploadRequestNotFound("not found"),
            404,
            "Upload request not found",
        ),
        (
            UploadRequestActivationConflict("conflict"),
            409,
            "Upload request cannot be activated",
        ),
    ],
)
def test_activate_request_maps_service_errors(
    authenticated_client,
    monkeypatch,
    error,
    expected_status,
    expected_detail,
):
    async def raise_service_error(**kwargs):
        raise error

    monkeypatch.setattr(
        "backend.app.api.routes.documents.activate_upload_request",
        raise_service_error,
    )

    response = authenticated_client.post(
        "/api/v1/upload-requests/42/activate"
    )

    assert response.status_code == expected_status
    assert response.json() == {"detail": expected_detail}


def test_activate_request_requires_authentication():
    app.dependency_overrides[get_database_session] = fake_database_session
    app.dependency_overrides[get_settings] = fake_settings

    try:
        with TestClient(app) as test_client:
            response = test_client.post(
                "/api/v1/upload-requests/42/activate"
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 401
    assert response.json() == {"detail": "Authentication required"}
    assert response.headers["www-authenticate"] == "Bearer"
