"""Base Model Provider abstraction layer."""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.models.enums import ErrorCategory, ExecutionStatus
from app.schemas.provider import GenerationParameters


class ProviderResult(BaseModel):
    """Output from an LLM provider invocation."""
    output_text: str
    latency_ms: float
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    status: ExecutionStatus = ExecutionStatus.SUCCESS
    error_category: ErrorCategory = ErrorCategory.NONE
    error_details: Optional[str] = None
    raw_metadata: Dict[str, Any] = Field(default_factory=dict)


class BaseModelProvider(ABC):
    """Abstract interface that all model providers must implement."""

    def __init__(self, name: str, base_url: Optional[str] = None):
        self.name = name
        self.base_url = base_url

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        model: str,
        system_prompt: Optional[str] = None,
        params: Optional[GenerationParameters] = None,
    ) -> ProviderResult:
        """Execute text generation with the given parameters."""
        pass

    @abstractmethod
    async def check_health(self) -> Dict[str, Any]:
        """Perform a live connectivity and readiness check."""
        pass

    @abstractmethod
    async def list_models(self) -> List[str]:
        """Return a list of available models for this provider."""
        pass

