from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

from fastapi import UploadFile


READ_CHUNK_SIZE = 1024 * 1024
SIGNATURE_LENGTH = 16
ALLOWED_EXTENSIONS = {
    "application/pdf": {".pdf"},
    "image/jpeg": {".jpg", ".jpeg"},
    "image/png": {".png"},
}


class EmptyUpload(ValueError):
    """Raised when an uploaded file contains no bytes."""


class UploadTooLarge(ValueError):
    """Raised when an uploaded file exceeds the configured limit."""


class InvalidUploadFilename(ValueError):
    """Raised when a display filename cannot be safely stored."""


class UnsupportedUploadType(ValueError):
    """Raised when file bytes and extension are not on the allowlist."""


@dataclass(frozen=True)
class InspectedUpload:
    original_filename: str
    content_type: str
    size_bytes: int
    sha256: str


def normalize_original_filename(filename: str | None) -> str:
    if filename is None:
        raise InvalidUploadFilename("A filename is required")

    normalized = filename.replace("\\", "/").rsplit("/", 1)[-1].strip()
    if not normalized or len(normalized) > 255 or "\x00" in normalized:
        raise InvalidUploadFilename("The filename is invalid")
    return normalized


def detect_content_type(signature: bytes) -> str:
    if signature.startswith(b"%PDF-"):
        return "application/pdf"
    if signature.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if signature.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    raise UnsupportedUploadType("The file type is not supported")


async def inspect_upload(
    file: UploadFile,
    *,
    max_size_bytes: int,
) -> InspectedUpload:
    original_filename = normalize_original_filename(file.filename)
    hasher = sha256()
    total_size = 0
    signature = bytearray()

    while chunk := await file.read(READ_CHUNK_SIZE):
        total_size += len(chunk)
        if total_size > max_size_bytes:
            await file.seek(0)
            raise UploadTooLarge("The uploaded file is too large")
        hasher.update(chunk)
        if len(signature) < SIGNATURE_LENGTH:
            missing = SIGNATURE_LENGTH - len(signature)
            signature.extend(chunk[:missing])

    await file.seek(0)

    if total_size == 0:
        raise EmptyUpload("The uploaded file is empty")

    content_type = detect_content_type(bytes(signature))
    extension = Path(original_filename).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS[content_type]:
        raise UnsupportedUploadType(
            "The filename extension does not match the file type"
        )

    return InspectedUpload(
        original_filename=original_filename,
        content_type=content_type,
        size_bytes=total_size,
        sha256=hasher.hexdigest(),
    )
