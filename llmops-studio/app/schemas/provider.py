"""Pydantic schemas for Model Providers and Configurations."""
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field
from app.models.enums import ProviderType


class GenerationParameters(BaseModel):
    """Runtime inference parameters."""
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=1024, ge=1, le=8192)
    top_p: float = Field(default=1.0, ge=0.0, le=1.0)
    timeout_seconds: int = Field(default=30, ge=1, le=120)


class ModelProviderCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    provider_type: ProviderType
    base_url: Optional[str] = None
    is_active: bool = True


class ModelProviderResponse(BaseModel):
    id: int
    name: str
    provider_type: ProviderType
    base_url: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ModelConfigCreate(BaseModel):
    provider_name: Optional[str] = "Mock"
    provider_id: Optional[int] = None
    model_identifier: str = Field(..., min_length=1, max_length=100)
    display_name: str = Field(..., min_length=1, max_length=150)
    description: Optional[str] = None
    default_temperature: float = 0.7
    default_max_tokens: int = 1024
    default_top_p: float = 1.0
    timeout_seconds: int = 30
    cost_per_1k_input_tokens: Optional[float] = None
    cost_per_1k_output_tokens: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None


class ModelConfigResponse(BaseModel):
    id: int
    provider_id: int
    provider_name: Optional[str] = None
    model_identifier: str
    display_name: str
    description: Optional[str] = None
    default_temperature: float
    default_max_tokens: int
    default_top_p: float
    timeout_seconds: int
    cost_per_1k_input_tokens: Optional[float] = None
    cost_per_1k_output_tokens: Optional[float] = None
    is_available: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ModelHealthCheckResponse(BaseModel):
    model_id: int
    model_identifier: str
    provider: str
    is_available: bool
    latency_ms: Optional[float] = None
    message: str

