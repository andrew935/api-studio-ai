import openai
from fastapi import APIRouter, Depends, HTTPException
from openai import AsyncOpenAI

from backend.app.schemas.llm import SupportClassification, SupportMessage
from backend.app.services.llm_client import (
    classify_support_message,
    create_openai_client,
)


router = APIRouter(prefix="/api/v1/ai")


@router.post(
    "/classify",
    response_model=SupportClassification,
)
async def classify_support(
    request: SupportMessage,
    client: AsyncOpenAI = Depends(create_openai_client),
):
    try:
        return await classify_support_message(
            request.message,
            client,
        )
    except openai.APITimeoutError:
        raise HTTPException(
            status_code=504,
            detail="OpenAI request timed out",
        )
    except openai.APIConnectionError:
        raise HTTPException(
            status_code=502,
            detail="OpenAI request connection error",
        )
    except openai.RateLimitError:
        raise HTTPException(
            status_code=503,
            detail="OpenAI request rate limit error",
        )
    except openai.APIError:
        raise HTTPException(
            status_code=500,
            detail="OpenAI request API error",
        )
