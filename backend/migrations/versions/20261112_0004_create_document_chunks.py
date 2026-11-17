"""Create document chunks.

Revision ID: 20261112_0004
Revises: 20261110_0003
Create Date: 2026-11-12

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20261112_0004"
down_revision: Union[str, Sequence[str], None] = "20261110_0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "document_chunks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("document_submission_id", sa.Integer(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "length(trim(content)) > 0",
            name="ck_document_chunks_content",
        ),
        sa.CheckConstraint(
            "position >= 0",
            name="ck_document_chunks_position",
        ),
        sa.ForeignKeyConstraint(
            ["document_submission_id"],
            ["document_submissions.id"],
            name="fk_document_chunks_submission",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "document_submission_id",
            "position",
            name="uq_document_chunks_submission_position",
        ),
    )
    op.create_index(
        op.f("ix_document_chunks_document_submission_id"),
        "document_chunks",
        ["document_submission_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_document_chunks_document_submission_id"),
        table_name="document_chunks",
    )
    op.drop_table("document_chunks")
