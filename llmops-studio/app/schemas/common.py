"""Common Pydantic schema helpers and generic responses."""
from typing import Any, Generic, List, Optional, TypeVar
from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class HealthStatus(BaseModel):
    """System health check payload."""
    status: str = "healthy"
    service: str = "LLMOps Studio"
    version: str = "1.0.0"
    database: str = "connected"
    timestamp: str


class StandardResponse(BaseModel, Generic[T]):
    """Standardized API response envelope."""
    success: bool = True
    message: Optional[str] = None
    data: Optional[T] = None


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic pagination wrapper."""
    total: int
    page: int = 1
    page_size: int = 50
    items: List[T]

