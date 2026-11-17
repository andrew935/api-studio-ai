import os

import pytest
from sqlalchemy import text

from backend.app.db.session import create_database_engine


POSTGRES_URL = os.getenv("TEST_POSTGRES_URL")

pytestmark = [
    pytest.mark.postgres,
    pytest.mark.skipif(
        not POSTGRES_URL,
        reason="TEST_POSTGRES_URL is required for PostgreSQL integration",
    ),
]


@pytest.mark.anyio
async def test_postgres_has_current_migration_and_core_tables():
    engine = create_database_engine(POSTGRES_URL)

    try:
        async with engine.connect() as connection:
            version = await connection.scalar(
                text("SELECT current_setting('server_version_num')")
            )
            rows = await connection.execute(
                text(
                    "SELECT tablename FROM pg_catalog.pg_tables "
                    "WHERE schemaname = 'public'"
                )
            )
            table_names = {row.tablename for row in rows}

        assert int(version) >= 180000
        assert {
            "alembic_version",
            "tenants",
            "users",
            "clients",
            "matters",
            "upload_requests",
            "document_requirements",
            "document_submissions",
        "document_chunks",
        }.issubset(table_names)
    finally:
        await engine.dispose()
