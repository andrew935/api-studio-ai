from hashlib import sha256
from io import BytesIO

import pytest
from fastapi import UploadFile
from starlette.datastructures import Headers

from backend.app.services.file_uploads import (
    EmptyUpload,
    InvalidUploadFilename,
    UploadTooLarge,
    UnsupportedUploadType,
    detect_content_type,
    inspect_upload,
    normalize_original_filename,
)


def make_upload(content: bytes, filename: str = "contract.pdf") -> UploadFile:
    return UploadFile(
        file=BytesIO(content),
        filename=filename,
        headers=Headers({"content-type": "application/pdf"}),
    )


@pytest.mark.anyio
async def test_inspect_upload_calculates_metadata_and_rewinds_file():
    content = b"%PDF-1.7 synthetic legal document"
    upload = make_upload(content, filename=r"C:\fakepath\contract.pdf")

    result = await inspect_upload(upload, max_size_bytes=15 * 1024 * 1024)

    assert result.original_filename == "contract.pdf"
    assert result.content_type == "application/pdf"
    assert result.size_bytes == len(content)
    assert result.sha256 == sha256(content).hexdigest()
    assert upload.file.read() == content


@pytest.mark.anyio
async def test_inspect_upload_rejects_file_over_limit_and_rewinds():
    upload = make_upload(b"12345")

    with pytest.raises(UploadTooLarge):
        await inspect_upload(upload, max_size_bytes=4)

    assert upload.file.read() == b"12345"


@pytest.mark.anyio
async def test_inspect_upload_rejects_empty_file():
    with pytest.raises(EmptyUpload):
        await inspect_upload(make_upload(b""), max_size_bytes=100)


@pytest.mark.parametrize(
    "filename",
    [None, "", "   ", "bad\x00name.pdf", "a" * 256],
)
def test_normalize_original_filename_rejects_invalid_value(filename):
    with pytest.raises(InvalidUploadFilename):
        normalize_original_filename(filename)


@pytest.mark.parametrize(
    ("signature", "expected_content_type"),
    [
        (b"%PDF-1.7", "application/pdf"),
        (b"\xff\xd8\xff\xe0", "image/jpeg"),
        (b"\x89PNG\r\n\x1a\n", "image/png"),
    ],
)
def test_detect_content_type_uses_file_signature(
    signature,
    expected_content_type,
):
    assert detect_content_type(signature) == expected_content_type


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("content", "filename"),
    [
        (b"plain text", "contract.pdf"),
        (b"%PDF-1.7 content", "contract.exe"),
        (b"\x89PNG\r\n\x1a\ncontent", "image.jpg"),
    ],
)
async def test_inspect_upload_rejects_unsupported_or_mismatched_type(
    content,
    filename,
):
    with pytest.raises(UnsupportedUploadType):
        await inspect_upload(
            make_upload(content, filename=filename),
            max_size_bytes=100,
        )
