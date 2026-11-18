from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


def create_database_engine(
    database_url: str,
    *,
    pool_timeout_seconds: float = 5,
    command_timeout_seconds: float = 5,
) -> AsyncEngine:
    options = {}
    if database_url.startswith("postgresql+asyncpg"):
        options = {
            "pool_pre_ping": True,
            "pool_timeout": pool_timeout_seconds,
            "connect_args": {"command_timeout": command_timeout_seconds},
        }

    return create_async_engine(database_url, **options)


def create_session_factory(
    engine: AsyncEngine,
) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)
