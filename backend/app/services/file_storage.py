import asyncio
import os
import shutil
from pathlib import Path
from typing import BinaryIO, Protocol
from uuid import uuid4

import boto3
from botocore.config import Config as BotoConfig
from botocore.exceptions import (
    ClientError,
    ConnectionClosedError,
    ConnectTimeoutError,
    EndpointConnectionError,
    ReadTimeoutError,
)

from backend.app.config import Settings
from backend.app.services.circuit_breaker import (
    CircuitBreaker,
    FailureDisposition,
)


class FileStorage(Protocol):
    async def save(
        self,
        *,
        file_object: BinaryIO,
        storage_key: str,
        content_type: str,
    ) -> None: ...

    async def delete(self, *, storage_key: str) -> None: ...

    async def close(self) -> None: ...


def generate_storage_key(tenant_id: int, upload_request_id: int) -> str:
    return (
        f"tenants/{tenant_id}/upload-requests/{upload_request_id}/"
        f"{uuid4()}"
    )


class LocalFileStorage:
    def __init__(self, root: Path):
        self.root = root.resolve()

    def _target_path(self, storage_key: str) -> Path:
        target = (self.root / storage_key).resolve()
        if not target.is_relative_to(self.root):
            raise ValueError("Storage key escapes the configured root")
        return target

    async def save(
        self,
        *,
        file_object: BinaryIO,
        storage_key: str,
        content_type: str,
    ) -> None:
        target = self._target_path(storage_key)
        temporary = target.with_name(f".{target.name}.{uuid4()}.tmp")

        def write_file() -> None:
            target.parent.mkdir(parents=True, exist_ok=True)
            try:
                with temporary.open("xb") as destination:
                    shutil.copyfileobj(file_object, destination)
                os.replace(temporary, target)
            finally:
                temporary.unlink(missing_ok=True)

        await asyncio.to_thread(write_file)

    async def delete(self, *, storage_key: str) -> None:
        target = self._target_path(storage_key)
        await asyncio.to_thread(target.unlink, missing_ok=True)

    async def close(self) -> None:
        return None


class S3FileStorage:
    def __init__(
        self,
        client,
        bucket: str,
        circuit_breaker: CircuitBreaker | None = None,
    ):
        self.client = client
        self.bucket = bucket
        self.circuit_breaker = circuit_breaker or CircuitBreaker(
            failure_threshold=3,
            recovery_timeout_seconds=30,
            classify_failure=classify_s3_failure,
        )

    async def save(
        self,
        *,
        file_object: BinaryIO,
        storage_key: str,
        content_type: str,
    ) -> None:
        async def upload() -> None:
            await asyncio.to_thread(
                self.client.upload_fileobj,
                file_object,
                self.bucket,
                storage_key,
                ExtraArgs={
                    "ContentType": content_type,
                    "ServerSideEncryption": "AES256",
                },
            )

        await self.circuit_breaker.call(upload)

    async def delete(self, *, storage_key: str) -> None:
        async def delete() -> None:
            await asyncio.to_thread(
                self.client.delete_object,
                Bucket=self.bucket,
                Key=storage_key,
            )

        await self.circuit_breaker.call(delete)

    async def close(self) -> None:
        await asyncio.to_thread(self.client.close)


def classify_s3_failure(error: Exception) -> FailureDisposition:
    if isinstance(
        error,
        (
            ConnectionClosedError,
            ConnectTimeoutError,
            EndpointConnectionError,
            ReadTimeoutError,
        ),
    ):
        return FailureDisposition.COUNT

    if not isinstance(error, ClientError):
        return FailureDisposition.IGNORE

    metadata = error.response.get("ResponseMetadata", {})
    status_code = metadata.get("HTTPStatusCode")
    error_code = str(error.response.get("Error", {}).get("Code", ""))

    if status_code in {401, 403}:
        return FailureDisposition.OPEN
    if isinstance(status_code, int) and status_code >= 500:
        return FailureDisposition.COUNT
    if error_code in {"RequestTimeout", "SlowDown", "Throttling"}:
        return FailureDisposition.COUNT

    return FailureDisposition.IGNORE


def create_file_storage(settings: Settings) -> FileStorage:
    if settings.storage_backend == "local":
        return LocalFileStorage(settings.local_storage_path)

    if not settings.s3_bucket:
        raise RuntimeError("S3_BUCKET is required when STORAGE_BACKEND=s3")

    endpoint_url = (
        str(settings.s3_endpoint_url).rstrip("/")
        if settings.s3_endpoint_url
        else None
    )
    client = boto3.client(
        "s3",
        region_name=settings.s3_region,
        endpoint_url=endpoint_url,
        config=BotoConfig(
            connect_timeout=settings.s3_connect_timeout_seconds,
            read_timeout=settings.s3_read_timeout_seconds,
            retries={
                "total_max_attempts": settings.s3_total_max_attempts,
                "mode": "standard",
            },
        ),
    )
    circuit_breaker = CircuitBreaker(
        failure_threshold=settings.s3_circuit_failure_threshold,
        recovery_timeout_seconds=settings.s3_circuit_recovery_seconds,
        classify_failure=classify_s3_failure,
    )
    return S3FileStorage(
        client=client,
        bucket=settings.s3_bucket,
        circuit_breaker=circuit_breaker,
    )
