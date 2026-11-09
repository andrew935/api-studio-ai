import sqlite3

from alembic import command
from alembic.config import Config


def test_initial_migration_upgrades_and_downgrades(tmp_path):
    database_path = tmp_path / "migration.db"
    alembic_config = Config("alembic.ini")
    alembic_config.set_main_option(
        "sqlalchemy.url",
        f"sqlite+aiosqlite:///{database_path.as_posix()}",
    )

    command.upgrade(alembic_config, "head")

    with sqlite3.connect(database_path) as connection:
        table_names = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }

    assert {
        "alembic_version",
        "tenants",
        "clients",
        "matters",
        "upload_requests",
    }.issubset(table_names)

    command.downgrade(alembic_config, "base")

    with sqlite3.connect(database_path) as connection:
        table_names = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }

    assert "tenants" not in table_names
    assert "clients" not in table_names
    assert "matters" not in table_names
    assert "upload_requests" not in table_names
