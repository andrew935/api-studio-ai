from typing import Literal

from pydantic import BaseModel, Field


class SupportClassification(BaseModel):
    category: Literal["billing", "technical", "other"]
    confidence: float = Field(ge=0, le=1, multiple_of=0.01)
    needs_human_review: bool


class SupportMessage(BaseModel):
    message: str = Field(min_length=1)


