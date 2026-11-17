from io import BytesIO

import pytest
from botocore.exceptions import ClientError, ReadTimeoutError

from backend.app.services.circuit_breaker import (
    CircuitBreaker,
    CircuitOpenError,
    CircuitState,
)
from backend.app.services.file_storage import (
    LocalFileStorage,
    S3FileStorage,
    classify_s3_failure,
    generate_storage_key,
)


class FakeS3Client:
    def __init__(self):
        self.upload = None
        self.deletion = None

    def upload_fileobj(
        self,
        file_object,
        bucket,
        key,
        *,
        ExtraArgs,
    ):
        self.upload = {
            "content": file_object.read(),
            "bucket": bucket,
            "key": key,
            "extra_args": ExtraArgs,
        }

    def delete_object(self, *, Bucket, Key):
        self.deletion = {"bucket": Bucket, "key": Key}


class FailingS3Client:
    def __init__(self, error):
        self.error = error
        self.calls = 0

    def upload_fileobj(self, *args, **kwargs):
        self.calls += 1
        raise self.error


def test_storage_key_is_server_generated_and_tenant_scoped():
    storage_key = generate_storage_key(tenant_id=7, upload_request_id=42)

    assert storage_key.startswith("tenants/7/upload-requests/42/")
    assert "contract.pdf" not in storage_key


@pytest.mark.anyio
async def test_local_storage_saves_and_deletes_inside_root(tmp_path):
    storage = LocalFileStorage(tmp_path)
    storage_key = "tenants/7/upload-requests/42/server-generated-id"

    await storage.save(
        file_object=BytesIO(b"synthetic document"),
        storage_key=storage_key,
        content_type="application/pdf",
    )

    target = tmp_path / storage_key
    assert target.read_bytes() == b"synthetic document"

    await storage.delete(storage_key=storage_key)
    assert not target.exists()


@pytest.mark.anyio
async def test_local_storage_rejects_path_traversal(tmp_path):
    storage = LocalFileStorage(tmp_path)

    with pytest.raises(ValueError):
        await storage.save(
            file_object=BytesIO(b"secret"),
            storage_key="../../outside.txt",
            content_type="text/plain",
        )


@pytest.mark.anyio
async def test_s3_storage_uploads_privately_with_server_side_encryption():
    client = FakeS3Client()
    storage = S3FileStorage(client=client, bucket="private-documents")

    await storage.save(
        file_object=BytesIO(b"synthetic document"),
        storage_key="tenants/7/upload-requests/42/server-generated-id",
        content_type="application/pdf",
    )

    assert client.upload == {
        "content": b"synthetic document",
        "bucket": "private-documents",
        "key": "tenants/7/upload-requests/42/server-generated-id",
        "extra_args": {
            "ContentType": "application/pdf",
            "ServerSideEncryption": "AES256",
        },
    }


@pytest.mark.anyio
async def test_s3_storage_deletes_by_server_generated_key():
    client = FakeS3Client()
    storage = S3FileStorage(client=client, bucket="private-documents")

    await storage.delete(
        storage_key="tenants/7/upload-requests/42/server-generated-id"
    )

    assert client.deletion == {
        "bucket": "private-documents",
        "key": "tenants/7/upload-requests/42/server-generated-id",
    }


@pytest.mark.anyio
async def test_s3_timeout_opens_circuit_after_threshold():
    client = FailingS3Client(
        ReadTimeoutError(endpoint_url="https://s3.example.com")
    )
    breaker = CircuitBreaker(
        failure_threshold=2,
        recovery_timeout_seconds=30,
        classify_failure=classify_s3_failure,
    )
    storage = S3FileStorage(
        client=client,
        bucket="private-documents",
        circuit_breaker=breaker,
    )

    for _ in range(2):
        with pytest.raises(ReadTimeoutError):
            await storage.save(
                file_object=BytesIO(b"synthetic document"),
                storage_key="synthetic-key",
                content_type="application/pdf",
            )

    with pytest.raises(CircuitOpenError):
        await storage.save(
            file_object=BytesIO(b"synthetic document"),
            storage_key="synthetic-key",
            content_type="application/pdf",
        )

    assert client.calls == 2
    assert breaker.state == CircuitState.OPEN


@pytest.mark.anyio
async def test_s3_403_opens_circuit_immediately():
    forbidden = ClientError(
        {
            "Error": {"Code": "AccessDenied", "Message": "denied"},
            "ResponseMetadata": {"HTTPStatusCode": 403},
        },
        "PutObject",
    )
    client = FailingS3Client(forbidden)
    breaker = CircuitBreaker(
        failure_threshold=5,
        recovery_timeout_seconds=30,
        classify_failure=classify_s3_failure,
    )
    storage = S3FileStorage(
        client=client,
        bucket="private-documents",
        circuit_breaker=breaker,
    )

    with pytest.raises(ClientError):
        await storage.save(
            file_object=BytesIO(b"synthetic document"),
            storage_key="synthetic-key",
            content_type="application/pdf",
        )

    assert breaker.state == CircuitState.OPEN
