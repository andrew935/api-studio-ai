"""Create core document tables.

Revision ID: 20261108_0001
Revises:
Create Date: 2026-11-08

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20261108_0001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tenants",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "clients",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "id",
            name="uq_clients_tenant_id_id",
        ),
    )
    op.create_index(
        op.f("ix_clients_tenant_id"),
        "clients",
        ["tenant_id"],
        unique=False,
    )
    op.create_table(
        "matters",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("client_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.ForeignKeyConstraint(
            ["tenant_id", "client_id"],
            ["clients.tenant_id", "clients.id"],
            name="fk_matters_tenant_client",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "client_id",
            "id",
            name="uq_matters_tenant_client_id",
        ),
    )
    op.create_table(
        "upload_requests",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("client_id", sa.Integer(), nullable=False),
        sa.Column("matter_id", sa.Integer(), nullable=True),
        sa.Column("token_hash", sa.String(length=64), nullable=True),
        sa.Column(
            "status",
            sa.String(length=20),
            server_default="draft",
            nullable=False,
        ),
        sa.Column(
            "expires_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column("max_files", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "max_files BETWEEN 1 AND 20",
            name="ck_upload_requests_max_files",
        ),
        sa.CheckConstraint(
            "(status = 'draft' AND token_hash IS NULL) OR "
            "(status IN ('active', 'completed', 'expired') "
            "AND token_hash IS NOT NULL) OR "
            "status = 'revoked'",
            name="ck_upload_requests_status_token",
        ),
        sa.CheckConstraint(
            "status IN ('draft', 'active', 'completed', "
            "'expired', 'revoked')",
            name="ck_upload_requests_status",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "client_id"],
            ["clients.tenant_id", "clients.id"],
            name="fk_upload_requests_tenant_client",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "client_id", "matter_id"],
            ["matters.tenant_id", "matters.client_id", "matters.id"],
            name="fk_upload_requests_tenant_client_matter",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index(
        op.f("ix_upload_requests_client_id"),
        "upload_requests",
        ["client_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_upload_requests_tenant_id"),
        "upload_requests",
        ["tenant_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_upload_requests_tenant_id"),
        table_name="upload_requests",
    )
    op.drop_index(
        op.f("ix_upload_requests_client_id"),
        table_name="upload_requests",
    )
    op.drop_table("upload_requests")
    op.drop_table("matters")
    op.drop_index(op.f("ix_clients_tenant_id"), table_name="clients")
    op.drop_table("clients")
    op.drop_table("tenants")
