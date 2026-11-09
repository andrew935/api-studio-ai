from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from backend.app.schemas.documents import (
    UploadRequest,
    UploadRequestActivationResponse,
)


def test_upload_request_uses_safe_defaults():
    upload_request = UploadRequest(
        client_id=10,
        expires_at=datetime(2026, 12, 1, tzinfo=UTC),
        max_files=3,
    )

    assert upload_request.matter_id is None
    assert upload_request.status == "draft"


@pytest.mark.parametrize("max_files", [0, 21])
def test_upload_request_rejects_invalid_file_limit(max_files):
    with pytest.raises(ValidationError):
        UploadRequest(
            client_id=10,
            expires_at=datetime(2026, 12, 1, tzinfo=UTC),
            max_files=max_files,
        )


def test_upload_request_rejects_unknown_status():
    with pytest.raises(ValidationError):
        UploadRequest(
            client_id=10,
            status="unknown",
            expires_at=datetime(2026, 12, 1, tzinfo=UTC),
            max_files=3,
        )


def test_activation_response_has_active_status_and_validated_url():
    response = UploadRequestActivationResponse(
        upload_request_id=42,
        upload_url="https://documents.example.com/upload/raw-token",
        expires_at=datetime(2026, 12, 1, tzinfo=UTC),
    )

    assert response.status == "active"
    assert str(response.upload_url).startswith("https://documents.example.com/")


def test_activation_response_rejects_invalid_url():
    with pytest.raises(ValidationError):
        UploadRequestActivationResponse(
            upload_request_id=42,
            upload_url="not-a-url",
            expires_at=datetime(2026, 12, 1, tzinfo=UTC),
        )
