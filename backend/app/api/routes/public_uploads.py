from datetime import UTC, datetime
from typing import Annotated

from fastapi import (
    APIRouter,
    Cookie,
    Depends,
    File,
    Header,
    HTTPException,
    Response,
    UploadFile,
)
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.dependencies import get_database_session, get_file_storage
from backend.app.config import Settings, get_settings
from backend.app.schemas.documents import (
    DocumentSubmissionResponse,
    UploadSessionResponse,
)
from backend.app.services.document_submissions import (
    FileStorageUnavailable,
    PublicUploadUnavailable,
    SubmissionFinalizationConflict,
    UploadFileLimitReached,
    create_document_submission,
)
from backend.app.services.file_storage import FileStorage
from backend.app.services.file_uploads import (
    EmptyUpload,
    InvalidUploadFilename,
    UnsupportedUploadType,
    UploadTooLarge,
)
from backend.app.services.upload_sessions import (
    InvalidUploadSession,
    UploadLinkUnavailable,
    create_upload_session,
    decode_upload_session,
    validate_upload_link,
)


UPLOAD_SESSION_COOKIE = "upload_session"

router = APIRouter(prefix="/api/v1/public/uploads", tags=["public-uploads"])


def get_upload_request_id(
    upload_session: Annotated[
        str | None,
        Cookie(alias=UPLOAD_SESSION_COOKIE),
    ] = None,
    settings: Settings = Depends(get_settings),
) -> int:
    if not upload_session:
        raise HTTPException(
            status_code=401,
            detail="Upload session required",
        )

    try:
        return decode_upload_session(upload_session, settings)
    except InvalidUploadSession:
        raise HTTPException(
            status_code=401,
            detail="Upload session required",
        )


@router.post(
    "/session",
    response_model=UploadSessionResponse,
)
async def exchange_upload_link(
    response: Response,
    raw_token: Annotated[
        str | None,
        Header(alias="X-Upload-Link-Token"),
    ] = None,
    session: AsyncSession = Depends(get_database_session),
    settings: Settings = Depends(get_settings),
) -> UploadSessionResponse:
    if not raw_token:
        raise HTTPException(
            status_code=404,
            detail="Upload link not found or unavailable",
        )

    try:
        upload_link = await validate_upload_link(session, raw_token)
        upload_session = create_upload_session(upload_link, settings)
    except UploadLinkUnavailable:
        raise HTTPException(
            status_code=404,
            detail="Upload link not found or unavailable",
        )

    max_age = max(
        0,
        int((upload_session.expires_at - datetime.now(UTC)).total_seconds()),
    )
    response.set_cookie(
        key=UPLOAD_SESSION_COOKIE,
        value=upload_session.token,
        max_age=max_age,
        expires=upload_session.expires_at,
        path="/api/v1/public/uploads",
        secure=settings.upload_cookie_secure,
        httponly=True,
        samesite="strict",
    )
    return UploadSessionResponse(expires_at=upload_session.expires_at)


@router.post(
    "/requirements/{document_requirement_id}/submissions",
    response_model=DocumentSubmissionResponse,
    status_code=201,
)
async def upload_document_submission(
    document_requirement_id: int,
    file: Annotated[UploadFile, File()],
    upload_request_id: int = Depends(get_upload_request_id),
    session: AsyncSession = Depends(get_database_session),
    settings: Settings = Depends(get_settings),
    storage: FileStorage = Depends(get_file_storage),
) -> DocumentSubmissionResponse:
    try:
        created = await create_document_submission(
            session=session,
            storage=storage,
            file=file,
            upload_request_id=upload_request_id,
            document_requirement_id=document_requirement_id,
            max_size_bytes=settings.max_upload_size_mb * 1024 * 1024,
        )
    except PublicUploadUnavailable:
        raise HTTPException(
            status_code=404,
            detail="Upload link not found or unavailable",
        )
    except UploadFileLimitReached:
        raise HTTPException(status_code=409, detail="Upload file limit reached")
    except UploadTooLarge:
        raise HTTPException(status_code=413, detail="Uploaded file is too large")
    except UnsupportedUploadType:
        raise HTTPException(status_code=415, detail="Unsupported file type")
    except (EmptyUpload, InvalidUploadFilename) as error:
        raise HTTPException(status_code=400, detail=str(error))
    except (FileStorageUnavailable, SubmissionFinalizationConflict):
        raise HTTPException(
            status_code=503,
            detail="Upload could not be completed",
        )
    finally:
        await file.close()

    return DocumentSubmissionResponse(
        submission_id=created.submission_id,
        original_filename=created.original_filename,
        size_bytes=created.size_bytes,
        sha256=created.sha256,
    )
