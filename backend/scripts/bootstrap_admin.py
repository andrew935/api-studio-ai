import asyncio
from getpass import getpass

from backend.app.config import get_settings
from backend.app.db.session import (
    create_database_engine,
    create_session_factory,
)
from backend.app.services.bootstrap import (
    BootstrapAdminConflict,
    bootstrap_admin,
)


async def run_bootstrap(
    tenant_name: str,
    email: str,
    password: str,
) -> None:
    settings = get_settings()
    engine = create_database_engine(settings.database_url)
    session_factory = create_session_factory(engine)

    try:
        async with session_factory() as session:
            result = await bootstrap_admin(
                session,
                tenant_name=tenant_name,
                email=email,
                password=password,
            )
    finally:
        await engine.dispose()

    print(
        f"Created admin {result.email} "
        f"for tenant {result.tenant_id} (user {result.user_id})."
    )


def main() -> None:
    tenant_name = input("Law firm name: ").strip()
    email = input("Admin email: ").strip()
    password = getpass("Password: ")
    password_confirmation = getpass("Confirm password: ")

    if password != password_confirmation:
        raise SystemExit("Passwords do not match.")

    try:
        asyncio.run(run_bootstrap(tenant_name, email, password))
    except (BootstrapAdminConflict, ValueError) as error:
        raise SystemExit(str(error)) from error


if __name__ == "__main__":
    main()
