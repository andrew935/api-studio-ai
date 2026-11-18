import asyncio

import openai
from fastapi import APIRouter, Depends, HTTPException
from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.dependencies import (
    AuthenticatedUser,
    get_current_user,
    get_current_tenant_id,
    get_database_session,
    get_openai_client,
)
from backend.app.config import Settings, get_settings
from backend.app.schemas.llm import SupportClassification, SupportMessage
from backend.app.schemas.rag import (
    DocumentAgentRequest,
    DocumentAgentResponse,
    RagAnswer,
    RagQuestion,
)
from backend.app.services.llm_client import classify_support_message
from backend.app.services.rag import answer_question_with_rag
from backend.app.services.sdk_agent import (
    answer_with_document_agent,
    document_agent_tools_for_role,
)


router = APIRouter(prefix="/api/v1/ai")


@router.post(
    "/classify",
    response_model=SupportClassification,
)
async def classify_support(
    request: SupportMessage,
    client: AsyncOpenAI = Depends(get_openai_client),
    settings: Settings = Depends(get_settings),
):
    try:
        async with asyncio.timeout(settings.openai_total_timeout_seconds):
            return await classify_support_message(
                request.message,
                client,
            )
    except TimeoutError:
        raise HTTPException(
            status_code=504,
            detail="OpenAI request timed out",
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


@router.post(
    "/rag/answer",
    response_model=RagAnswer,
)
async def answer_rag_question(
    request: RagQuestion,
    tenant_id: int = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(get_database_session),
    client: AsyncOpenAI = Depends(get_openai_client),
    settings: Settings = Depends(get_settings),
) -> RagAnswer:
    try:
        async with asyncio.timeout(settings.openai_total_timeout_seconds):
            return await answer_question_with_rag(
                request.question,
                tenant_id=tenant_id,
                session=session,
                client=client,
                limit=request.limit,
            )
    except TimeoutError:
        raise HTTPException(
            status_code=504,
            detail="OpenAI request timed out",
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))
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


@router.post(
    "/agent/documents/answer",
    response_model=DocumentAgentResponse,
)
async def answer_document_agent(
    request: DocumentAgentRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_database_session),
    settings: Settings = Depends(get_settings),
) -> DocumentAgentResponse:
    try:
        async with asyncio.timeout(settings.openai_total_timeout_seconds):
            answer = await answer_with_document_agent(
                request.message,
                user_id=current_user.user_id,
                tenant_id=current_user.tenant_id,
                database_session=session,
                allowed_tools=document_agent_tools_for_role(current_user.role),
            )
    except TimeoutError:
        raise HTTPException(
            status_code=504,
            detail="OpenAI request timed out",
        )
    except PermissionError:
        raise HTTPException(status_code=403, detail="Tool is not permitted")
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

    return DocumentAgentResponse(answer=answer)
