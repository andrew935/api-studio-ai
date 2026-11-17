from backend.app.config import get_settings
from backend.app.mcp_server import create_document_mcp_server


def main() -> None:
    settings = get_settings()
    server = create_document_mcp_server(settings)
    server.run(
        transport="streamable-http",
        host=settings.mcp_bind_host,
        port=settings.mcp_bind_port,
        streamable_http_path="/mcp",
    )


if __name__ == "__main__":
    main()
