from fastapi import FastAPI

from backend.app.api.routes import ai, requests, root


app = FastAPI()
app.include_router(root.router)
app.include_router(requests.router)
app.include_router(ai.router)
