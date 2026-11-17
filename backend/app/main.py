from contextlib import asynccontextmanager

from fastapi import FastAPI
from prometheus_client import make_asgi_app

from backend.app.api.routes import (
    ai,
    auth,
    documents,
    health,
    public_uploads,
    requests,
    root,
)
from backend.app.config import get_settings
from backend.app.db.session import (
    create_database_engine,
    create_session_factory,
)
from backend.app.services.file_storage import create_file_storage
from backend.app.logging import configure_logging, log_http_request


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_logging(settings.log_level)
    engine = create_database_engine(settings.database_url)
    app.state.database_session_factory = create_session_factory(engine)
    app.state.file_storage = create_file_storage(settings)

    try:
        yield
    finally:
        await app.state.file_storage.close()
        await engine.dispose()


app = FastAPI(lifespan=lifespan)
app.middleware("http")(log_http_request)
app.mount("/metrics", make_asgi_app())
app.include_router(root.router)
app.include_router(health.router)
app.include_router(requests.router)
app.include_router(ai.router)
app.include_router(auth.router)
app.include_router(documents.router)
app.include_router(public_uploads.router)
