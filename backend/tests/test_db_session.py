from backend.app.db.session import create_database_engine


def test_postgres_engine_uses_explicit_pool_and_command_timeouts(monkeypatch):
    captured = {}
    expected_engine = object()

    def fake_create_async_engine(database_url, **options):
        captured["database_url"] = database_url
        captured["options"] = options
        return expected_engine

    monkeypatch.setattr(
        "backend.app.db.session.create_async_engine",
        fake_create_async_engine,
    )

    engine = create_database_engine(
        "postgresql+asyncpg://app:secret@db/app",
        pool_timeout_seconds=4,
        command_timeout_seconds=6,
    )

    assert engine is expected_engine
    assert captured == {
        "database_url": "postgresql+asyncpg://app:secret@db/app",
        "options": {
            "pool_pre_ping": True,
            "pool_timeout": 4,
            "connect_args": {"command_timeout": 6},
        },
    }


def test_sqlite_engine_does_not_receive_postgres_only_options(monkeypatch):
    captured = {}

    def fake_create_async_engine(database_url, **options):
        captured.update(options)
        return object()

    monkeypatch.setattr(
        "backend.app.db.session.create_async_engine",
        fake_create_async_engine,
    )

    create_database_engine("sqlite+aiosqlite:///:memory:")

    assert captured == {}
