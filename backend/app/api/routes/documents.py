from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.dependencies import (
    get_current_tenant_id,
    get_database_session,
)
from backend.app.config import Settings, get_settings
from backend.app.schemas.documents import UploadRequestActivationResponse
from backend.app.services.upload_requests import (
    UploadRequestActivationConflict,
    UploadRequestNotFound,
    activate_upload_request,
)


router = APIRouter(
    prefix="/api/v1/upload-requests",
    tags=["upload-requests"],
)


@router.post(
    "/{upload_request_id}/activate",
    response_model=UploadRequestActivationResponse,
)
async def activate_request(
    upload_request_id: int,
    tenant_id: int = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(get_database_session),
    settings: Settings = Depends(get_settings),
) -> UploadRequestActivationResponse:
    try:
        activation = await activate_upload_request(
            session=session,
            tenant_id=tenant_id,
            upload_request_id=upload_request_id,
        )
    except UploadRequestNotFound:
        raise HTTPException(
            status_code=404,
            detail="Upload request not found",
        )
    except UploadRequestActivationConflict:
        raise HTTPException(
            status_code=409,
            detail="Upload request cannot be activated",
        )

    public_base_url = str(settings.public_base_url).rstrip("/")
    upload_url = f"{public_base_url}/upload#token={activation.raw_token}"

    return UploadRequestActivationResponse(
        upload_request_id=activation.upload_request_id,
        upload_url=upload_url,
        expires_at=activation.expires_at,
    )
