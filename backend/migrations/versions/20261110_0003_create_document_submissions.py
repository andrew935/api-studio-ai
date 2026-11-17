"""Create document requirements and submissions.

Revision ID: 20261110_0003
Revises: 20261109_0002
Create Date: 2026-11-10

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20261110_0003"
down_revision: Union[str, Sequence[str], None] = "20261109_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "document_requirements",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("upload_request_id", sa.Integer(), nullable=False),
        sa.Column("label", sa.String(length=200), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["upload_request_id"],
            ["upload_requests.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_document_requirements_upload_request_id"),
        "document_requirements",
        ["upload_request_id"],
        unique=False,
    )
    op.create_table(
        "document_submissions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("document_requirement_id", sa.Integer(), nullable=False),
        sa.Column("storage_key", sa.String(length=500), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=255), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column(
            "status",
            sa.String(length=30),
            server_default="pending_scan",
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "size_bytes > 0",
            name="ck_document_submissions_size_bytes",
        ),
        sa.CheckConstraint(
            "status IN ('uploading', 'pending_scan', 'pending_review', "
            "'approved', 'rejected', 'scan_failed', 'upload_failed')",
            name="ck_document_submissions_status",
        ),
        sa.ForeignKeyConstraint(
            ["document_requirement_id"],
            ["document_requirements.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("storage_key"),
    )
    op.create_index(
        op.f("ix_document_submissions_document_requirement_id"),
        "document_submissions",
        ["document_requirement_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_document_submissions_sha256"),
        "document_submissions",
        ["sha256"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_document_submissions_sha256"),
        table_name="document_submissions",
    )
    op.drop_index(
        op.f("ix_document_submissions_document_requirement_id"),
        table_name="document_submissions",
    )
    op.drop_table("document_submissions")
    op.drop_index(
        op.f("ix_document_requirements_upload_request_id"),
        table_name="document_requirements",
    )
    op.drop_table("document_requirements")
