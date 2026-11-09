from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.documents import UploadRequestRow
from backend.app.schemas.documents import UploadRequestStatus
from backend.app.services.upload_tokens import (
    generate_upload_token,
    hash_upload_token,
)


ALLOWED_STATUS_TRANSITIONS: dict[
    UploadRequestStatus,
    set[UploadRequestStatus],
] = {
    "draft": {"active", "revoked"},
    "active": {"completed", "expired", "revoked"},
    "completed": set(),
    "expired": set(),
    "revoked": set(),
}


@dataclass(frozen=True)
class ActivatedUploadRequest:
    upload_request_id: int
    raw_token: str
    expires_at: datetime


class InvalidUploadRequestStatusTransition(ValueError):
    """Raised when an upload request cannot enter the target status."""


class UploadRequestActivationConflict(RuntimeError):
    """Raised when an upload request cannot be activated atomically."""


class UploadRequestNotFound(LookupError):
    """Raised when an upload request is outside the current tenant scope."""


def validate_status_transition(
    current_status: UploadRequestStatus,
    target_status: UploadRequestStatus,
) -> bool:
    """Return whether a write is needed or raise for an invalid transition."""

    if current_status == target_status:
        return False

    if target_status not in ALLOWED_STATUS_TRANSITIONS[current_status]:
        raise InvalidUploadRequestStatusTransition(
            f"Cannot transition upload request from "
            f"{current_status} to {target_status}"
        )

    return True


async def activate_upload_request(
    session: AsyncSession,
    tenant_id: int,
    upload_request_id: int,
) -> ActivatedUploadRequest:
    """Activate a draft atomically and return its one-time result."""

    raw_token = generate_upload_token()
    token_hash = hash_upload_token(raw_token)

    try:
        result = await session.execute(
            update(UploadRequestRow)
            .where(
                UploadRequestRow.id == upload_request_id,
                UploadRequestRow.tenant_id == tenant_id,
                UploadRequestRow.status == "draft",
            )
            .values(
                status="active",
                token_hash=token_hash,
            )
            .returning(
                UploadRequestRow.id,
                UploadRequestRow.expires_at,
            )
        )

        activation_row = result.one_or_none()

        if activation_row is None:
            existing_request_id = await session.scalar(
                select(UploadRequestRow.id).where(
                    UploadRequestRow.id == upload_request_id,
                    UploadRequestRow.tenant_id == tenant_id,
                )
            )

            if existing_request_id is None:
                raise UploadRequestNotFound("Upload request not found")

            raise UploadRequestActivationConflict(
                "Upload request is not available for activation"
            )

        await session.commit()
    except Exception:
        await session.rollback()
        raise

    return ActivatedUploadRequest(
        upload_request_id=activation_row.id,
        raw_token=raw_token,
        expires_at=activation_row.expires_at,
    )
