from types import SimpleNamespace

import pytest

from backend.app.config import Settings
from backend.app.mcp_server import (
    DOCUMENT_READ_SCOPE,
    JwtTokenVerifier,
    create_document_mcp_server,
    search_documents_for_mcp,
)
from backend.app.services.security import create_access_token


def make_settings() -> Settings:
    return Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        public_base_url="https://documents.example.com",
        jwt_secret_key="test-secret-key-with-at-least-32-characters",
        jwt_issuer="api-studio-ai-tests",
        jwt_audience="api-studio-ai-test-api",
        access_token_expire_minutes=30,
        mcp_server_url="https://mcp.documents.example.com/mcp",
        mcp_auth_issuer_url="https://documents.example.com",
    )


class FakeSession:
    def __init__(self, user):
        self.user = user

    async def scalar(self, statement):
        return self.user


@pytest.mark.anyio
async def test_mcp_token_verifier_accepts_existing_access_token():
    settings = make_settings()
    raw_token = create_access_token(17, settings)

    token = await JwtTokenVerifier(settings).verify_token(raw_token)

    assert token is not None
    assert token.subject == "17"
    assert token.scopes == [DOCUMENT_READ_SCOPE]
    assert token.resource == "https://mcp.documents.example.com/mcp"


@pytest.mark.anyio
async def test_mcp_token_verifier_rejects_untrusted_token():
    token = await JwtTokenVerifier(make_settings()).verify_token("invalid")

    assert token is None


@pytest.mark.anyio
async def test_mcp_tool_schema_does_not_expose_identity():
    server = create_document_mcp_server(make_settings())

    tools = await server.list_tools()

    assert len(tools) == 1
    assert tools[0].name == "search_documents"
    assert set(tools[0].input_schema["properties"]) == {"query", "limit"}
    assert tools[0].input_schema["required"] == ["query"]


@pytest.mark.anyio
async def test_mcp_search_uses_tenant_from_database(monkeypatch):
    captured = {}

    async def fake_search(
        session,
        *,
        tenant_id: int,
        query: str,
        limit: int,
    ) -> dict[str, object]:
        captured.update(
            tenant_id=tenant_id,
            query=query,
            limit=limit,
        )
        return {"context": "contract text", "sources": []}

    monkeypatch.setattr(
        "backend.app.mcp_server.search_tenant_documents",
        fake_search,
    )
    session = FakeSession(
        SimpleNamespace(
            id=17,
            tenant_id=7,
            role="staff",
            is_active=True,
        )
    )

    result = await search_documents_for_mcp(
        session,
        user_id=17,
        query="termination clause",
        limit=4,
    )

    assert captured == {
        "tenant_id": 7,
        "query": "termination clause",
        "limit": 4,
    }
    assert result["context"] == "contract text"


@pytest.mark.anyio
async def test_mcp_search_rejects_inactive_user():
    session = FakeSession(
        SimpleNamespace(
            id=17,
            tenant_id=7,
            role="staff",
            is_active=False,
        )
    )

    with pytest.raises(PermissionError, match="Authentication required"):
        await search_documents_for_mcp(
            session,
            user_id=17,
            query="contract",
        )
