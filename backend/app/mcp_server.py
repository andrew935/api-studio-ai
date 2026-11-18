from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass

from mcp.server import MCPServer
from mcp.server.auth.middleware.auth_context import get_access_token
from mcp.server.auth.provider import AccessToken
from mcp.server.auth.settings import AuthSettings
from mcp.server.mcpserver import Context
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.app.config import Settings
from backend.app.db.session import (
    create_database_engine,
    create_session_factory,
)
from backend.app.services.auth import load_active_user
from backend.app.services.document_search import search_tenant_documents
from backend.app.services.security import (
    InvalidAccessToken,
    decode_access_token,
)


DOCUMENT_READ_SCOPE = "documents:read"
DOCUMENT_READER_ROLES = frozenset({"admin", "staff"})


class JwtTokenVerifier:
    def __init__(self, settings: Settings):
        self._settings = settings

    async def verify_token(self, token: str) -> AccessToken | None:
        try:
            user_id = decode_access_token(token, self._settings)
        except InvalidAccessToken:
            return None

        return AccessToken(
            token=token,
            client_id="api-studio-ai",
            subject=str(user_id),
            scopes=[DOCUMENT_READ_SCOPE],
            resource=str(self._settings.mcp_server_url),
            claims={"iss": self._settings.jwt_issuer},
        )


@dataclass(frozen=True)
class DocumentMcpResources:
    session_factory: async_sessionmaker[AsyncSession]


async def search_documents_for_mcp(
    session: AsyncSession,
    *,
    user_id: int,
    query: str,
    limit: int = 3,
) -> dict[str, object]:
    user = await load_active_user(session, user_id)
    if user is None:
        raise PermissionError("Authentication required")
    if user.role not in DOCUMENT_READER_ROLES:
        raise PermissionError("Tool is not permitted")

    return await search_tenant_documents(
        session,
        tenant_id=user.tenant_id,
        query=query,
        limit=limit,
    )


def create_document_mcp_server(settings: Settings) -> MCPServer:
    @asynccontextmanager
    async def lifespan(
        _server: MCPServer,
    ) -> AsyncIterator[DocumentMcpResources]:
        engine = create_database_engine(
            settings.database_url,
            pool_timeout_seconds=settings.database_pool_timeout_seconds,
            command_timeout_seconds=settings.database_command_timeout_seconds,
        )
        try:
            yield DocumentMcpResources(
                session_factory=create_session_factory(engine)
            )
        finally:
            await engine.dispose()

    server = MCPServer(
        "secure-document-hub",
        instructions=(
            "Search only approved documents available to the authenticated "
            "API Studio AI user."
        ),
        lifespan=lifespan,
        token_verifier=JwtTokenVerifier(settings),
        auth=AuthSettings(
            issuer_url=settings.mcp_auth_issuer_url,
            resource_server_url=settings.mcp_server_url,
            validate_token_resource=False,
            required_scopes=[DOCUMENT_READ_SCOPE],
        ),
    )

    @server.tool()
    async def search_documents(
        query: str,
        ctx: Context,
        limit: int = 3,
    ) -> dict[str, object]:
        """Search approved documents in the authenticated user's tenant."""
        token = get_access_token()
        if token is None or token.subject is None:
            raise PermissionError("Authentication required")

        try:
            user_id = int(token.subject)
        except ValueError:
            raise PermissionError("Authentication required") from None

        resources = ctx.request_context.lifespan_context
        async with resources.session_factory() as session:
            return await search_documents_for_mcp(
                session,
                user_id=user_id,
                query=query,
                limit=limit,
            )

    return server
