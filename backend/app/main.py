from contextlib import asynccontextmanager

from fastapi import FastAPI

from backend.app.api.routes import (
    ai,
    auth,
    documents,
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    engine = create_database_engine(settings.database_url)
    app.state.database_session_factory = create_session_factory(engine)
    app.state.file_storage = create_file_storage(settings)

    try:
        yield
    finally:
        await app.state.file_storage.close()
        await engine.dispose()


app = FastAPI(lifespan=lifespan)
app.include_router(root.router)
app.include_router(requests.router)
app.include_router(ai.router)
app.include_router(auth.router)
app.include_router(documents.router)
app.include_router(public_uploads.router)
