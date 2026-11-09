from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    String,
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
