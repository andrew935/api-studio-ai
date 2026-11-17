from pydantic import BaseModel, Field


class DocumentAgentRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)


class DocumentAgentResponse(BaseModel):
    answer: str = Field(min_length=1)


class RagQuestion(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    limit: int = Field(default=3, ge=1, le=10)


class RagSource(BaseModel):
    chunk_id: int = Field(gt=0)
    document_submission_id: int = Field(gt=0)
    position: int = Field(ge=0)


class RagAnswer(BaseModel):
    answer: str = Field(min_length=1)
    sources: list[RagSource]
