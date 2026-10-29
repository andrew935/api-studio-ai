from fastapi import APIRouter, Depends, HTTPException

from backend.app.schemas.requests import APIRequest
from backend.app.services.http_client import fetch_demo_users

router = APIRouter(prefix="/api/v1/requests")


@router.post("/preview")
def preview_request(request: APIRequest):
    return {
        "url": request.url,
        "method": request.method,
        "status": "ready",
    }


@router.get("/test")
async def test_request(result: dict = Depends(fetch_demo_users)):
    if result.get("error_type") == "timeout":
        raise HTTPException(status_code=504, detail=result["message"])
    elif result.get("error_type") == "http_error":
        raise HTTPException(status_code=502, detail=result["message"])

    return result

