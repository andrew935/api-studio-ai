"""Create transactional outbox jobs.

Revision ID: 20261116_0005
Revises: 20261112_0004
Create Date: 2026-11-16

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20261116_0005"
down_revision: Union[str, Sequence[str], None] = "20261112_0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "outbox_jobs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("aggregate_id", sa.Integer(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=255), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column(
            "status",
            sa.String(length=20),
            server_default="pending",
            nullable=False,
        ),
        sa.Column(
            "attempt_count",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "available_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "attempt_count >= 0",
            name="ck_outbox_jobs_attempt_count",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'processing', 'completed', 'failed')",
            name="ck_outbox_jobs_status",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "idempotency_key",
            name="uq_outbox_jobs_idempotency_key",
        ),
    )
    op.create_index(
        op.f("ix_outbox_jobs_aggregate_id"),
        "outbox_jobs",
        ["aggregate_id"],
        unique=False,
    )
    op.create_index(
        "ix_outbox_jobs_claimable",
        "outbox_jobs",
        ["status", "available_at", "id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_outbox_jobs_claimable", table_name="outbox_jobs")
    op.drop_index(
        op.f("ix_outbox_jobs_aggregate_id"),
        table_name="outbox_jobs",
    )
    op.drop_table("outbox_jobs")
