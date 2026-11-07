"""Pydantic schemas for Prompt templates, versions, and execution."""
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.provider import GenerationParameters


class PromptVersionCreate(BaseModel):
    template_text: str = Field(..., min_length=1)
    system_prompt: Optional[str] = None
    description: Optional[str] = None


class PromptVersionResponse(BaseModel):
    id: int
    prompt_id: int
    version_number: int
    template_text: str
    input_variables: List[str] = []
    system_prompt: Optional[str] = None
    description: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PromptCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=150)
    description: Optional[str] = None
    tags: Optional[str] = None
    initial_template: str = Field(..., min_length=1)
    system_prompt: Optional[str] = None


class PromptResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    tags: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    latest_version: Optional[PromptVersionResponse] = None
    versions_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class PromptDetailResponse(PromptResponse):
    versions: List[PromptVersionResponse] = []


class PromptExecuteRequest(BaseModel):
    model_id: int
    variables: Dict[str, Any] = {}
    parameters: Optional[GenerationParameters] = None


class PromptExecuteResponse(BaseModel):
    execution_id: int
    request_id: str
    model_name: str
    rendered_prompt: str
    output_text: str
    latency_ms: float
    input_tokens: int
    output_tokens: int
    total_tokens: int
    status: str

