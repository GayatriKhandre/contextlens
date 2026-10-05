from __future__ import annotations

from typing import Any, Optional
from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    problem: str = Field(min_length=20, max_length=12000)
    about: str = Field(default="not_sure")
    mode: str = Field(default="think")
    use_personal_context: bool = False


class ContinueRequest(BaseModel):
    case_id: str
    answer: str = Field(default="")
    skipped: bool = False


class DecisionRequest(BaseModel):
    case_id: str
    decision: str = Field(min_length=5, max_length=4000)
    confidence: Optional[int] = Field(default=None, ge=1, le=5)
    review_date: Optional[str] = None


class PersonalContextRequest(BaseModel):
    content: str = Field(default="", max_length=4000)
    enabled: bool = False


class CaseRecord(BaseModel):
    id: str
    title: str
    preview: str
    status: str
    created_at: str
    updated_at: str
    problem: str
    about: str
    mode: str
    use_personal_context: bool
    context: dict[str, Any] = {}
    question: dict[str, Any] = {}
    analysis: dict[str, Any] = {}
    decision: Optional[dict[str, Any]] = None


class ApiError(BaseModel):
    error: str
    detail: str
    code: str
