from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    Index,
    JSON,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base


UPLOAD_REQUEST_STATUSES = (
    "draft",
    "active",
    "completed",
    "expired",
    "revoked",
)

DOCUMENT_SUBMISSION_STATUSES = (
    "uploading",
    "pending_scan",
    "pending_review",
    "approved",
    "rejected",
    "scan_failed",
    "upload_failed",
)

OUTBOX_JOB_STATUSES = (
    "pending",
    "processing",
    "completed",
    "failed",
)


class TenantRow(Base):
    __tablename__ = "tenants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)


class ClientRow(Base):
    __tablename__ = "clients"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "id",
            name="uq_clients_tenant_id_id",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)


class MatterRow(Base):
    __tablename__ = "matters"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "client_id"],
            ["clients.tenant_id", "clients.id"],
            ondelete="CASCADE",
            name="fk_matters_tenant_client",
        ),
        UniqueConstraint(
            "tenant_id",
            "client_id",
            "id",
            name="uq_matters_tenant_client_id",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(Integer, nullable=False)
    client_id: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)


class UploadRequestRow(Base):
    __tablename__ = "upload_requests"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "client_id"],
            ["clients.tenant_id", "clients.id"],
            ondelete="CASCADE",
            name="fk_upload_requests_tenant_client",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "client_id", "matter_id"],
            ["matters.tenant_id", "matters.client_id", "matters.id"],
            ondelete="CASCADE",
            name="fk_upload_requests_tenant_client_matter",
        ),
        CheckConstraint(
            "status IN ('draft', 'active', 'completed', "
            "'expired', 'revoked')",
            name="ck_upload_requests_status",
        ),
        CheckConstraint(
            "max_files BETWEEN 1 AND 20",
            name="ck_upload_requests_max_files",
        ),
        CheckConstraint(
            "(status = 'draft' AND token_hash IS NULL) OR "
            "(status IN ('active', 'completed', 'expired') "
            "AND token_hash IS NOT NULL) OR "
            "status = 'revoked'",
            name="ck_upload_requests_status_token",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    client_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    matter_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    token_hash: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        unique=True,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="draft",
        server_default="draft",
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    max_files: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class DocumentRequirementRow(Base):
    __tablename__ = "document_requirements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    upload_request_id: Mapped[int] = mapped_column(
        ForeignKey("upload_requests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    label: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class DocumentSubmissionRow(Base):
    __tablename__ = "document_submissions"
    __table_args__ = (
        CheckConstraint(
            "status IN ('uploading', 'pending_scan', 'pending_review', "
            "'approved', 'rejected', 'scan_failed', 'upload_failed')",
            name="ck_document_submissions_status",
        ),
        CheckConstraint(
            "size_bytes > 0",
            name="ck_document_submissions_size_bytes",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_requirement_id: Mapped[int] = mapped_column(
        ForeignKey("document_requirements.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    storage_key: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        unique=True,
    )
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(255), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="pending_scan",
        server_default="pending_scan",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class DocumentChunkRow(Base):
    __tablename__ = "document_chunks"
    __table_args__ = (
        UniqueConstraint(
            "document_submission_id",
            "position",
            name="uq_document_chunks_submission_position",
        ),
        CheckConstraint(
            "position >= 0",
            name="ck_document_chunks_position",
        ),
        CheckConstraint(
            "length(trim(content)) > 0",
            name="ck_document_chunks_content",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_submission_id: Mapped[int] = mapped_column(
        ForeignKey("document_submissions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class OutboxJobRow(Base):
    __tablename__ = "outbox_jobs"
    __table_args__ = (
        Index(
            "ix_outbox_jobs_claimable",
            "status",
            "available_at",
            "id",
        ),
        CheckConstraint(
            "status IN ('pending', 'processing', 'completed', 'failed')",
            name="ck_outbox_jobs_status",
        ),
        CheckConstraint(
            "attempt_count >= 0",
            name="ck_outbox_jobs_attempt_count",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    aggregate_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    idempotency_key: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
    )
    payload: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        server_default="pending",
    )
    attempt_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    available_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    locked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
