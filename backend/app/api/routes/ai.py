import openai
from fastapi import APIRouter, Depends, HTTPException
from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.dependencies import (
    AuthenticatedUser,
    get_current_user,
    get_current_tenant_id,
    get_database_session,
)
from backend.app.schemas.llm import SupportClassification, SupportMessage
from backend.app.schemas.rag import (
    DocumentAgentRequest,
    DocumentAgentResponse,
    RagAnswer,
    RagQuestion,
)
from backend.app.services.llm_client import (
    classify_support_message,
    create_openai_client,
)
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


@router.post(
    "/rag/answer",
    response_model=RagAnswer,
)
async def answer_rag_question(
    request: RagQuestion,
    tenant_id: int = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(get_database_session),
    client: AsyncOpenAI = Depends(create_openai_client),
) -> RagAnswer:
    try:
        return await answer_question_with_rag(
            request.question,
            tenant_id=tenant_id,
            session=session,
            client=client,
            limit=request.limit,
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
) -> DocumentAgentResponse:
    try:
        answer = await answer_with_document_agent(
            request.message,
            user_id=current_user.user_id,
            tenant_id=current_user.tenant_id,
            database_session=session,
            allowed_tools=document_agent_tools_for_role(current_user.role),
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
