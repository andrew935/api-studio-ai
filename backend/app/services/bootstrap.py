from dataclasses import dataclass

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.documents import TenantRow
from backend.app.models.users import UserRow
from backend.app.services.security import hash_password


@dataclass(frozen=True)
class BootstrappedAdmin:
    tenant_id: int
    user_id: int
    email: str


class BootstrapAdminConflict(RuntimeError):
    """Raised when the initial tenant and admin cannot be created."""


async def bootstrap_admin(
    session: AsyncSession,
    *,
    tenant_name: str,
    email: str,
    password: str,
) -> BootstrappedAdmin:
    normalized_tenant_name = tenant_name.strip()
    normalized_email = email.strip().lower()

    if not normalized_tenant_name:
        raise ValueError("Tenant name is required")
    if len(password) < 12:
        raise ValueError("Password must contain at least 12 characters")

    try:
        tenant = TenantRow(name=normalized_tenant_name)
        session.add(tenant)
        await session.flush()

        user = UserRow(
            tenant_id=tenant.id,
            email=normalized_email,
            password_hash=hash_password(password),
            role="admin",
        )
        session.add(user)
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise BootstrapAdminConflict(
            "An account with this email already exists"
        ) from None
    except Exception:
        await session.rollback()
        raise

    return BootstrappedAdmin(
        tenant_id=tenant.id,
        user_id=user.id,
        email=user.email,
    )
