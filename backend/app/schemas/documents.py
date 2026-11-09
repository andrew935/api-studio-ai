from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl


UploadRequestStatus = Literal[
    "draft",
    "active",
    "completed",
    "expired",
    "revoked",
]


class UploadRequest(BaseModel):
    client_id: int
    matter_id: int | None = None
    status: UploadRequestStatus = "draft"
    expires_at: datetime
    max_files: int = Field(ge=1, le=20)


class UploadRequestActivationResponse(BaseModel):
    upload_request_id: int
    status: Literal["active"] = "active"
    upload_url: HttpUrl
    expires_at: datetime
