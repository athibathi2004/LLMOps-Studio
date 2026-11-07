"""Pydantic schemas for Model Execution Traces and Execution Logs."""
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict
from app.models.enums import ErrorCategory, ExecutionStatus
from app.schemas.evaluation import EvaluationResultResponse


class ExecutionLogItem(BaseModel):
    timestamp: datetime
    level: str
    message: str
    metadata: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)


class ModelExecutionSummary(BaseModel):
    id: int
    request_id: str
    model_identifier: str
    model_name: str
    status: ExecutionStatus
    error_category: ErrorCategory
    latency_ms: float
    total_tokens: int
    cost_estimate: Optional[float] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ModelExecutionDetail(BaseModel):
    id: int
    request_id: str
    experiment_id: Optional[int] = None
    experiment_run_id: Optional[int] = None
    model_config_id: int
    model_identifier: str
    model_name: str
    provider_name: str
    input_prompt: str
    output_text: Optional[str] = None
    status: ExecutionStatus
    error_category: ErrorCategory
    error_details: Optional[str] = None
    start_time: datetime
    end_time: Optional[datetime] = None
    latency_ms: float
    input_tokens: int
    output_tokens: int
    total_tokens: int
    generation_parameters: Optional[Dict[str, Any]] = None
    cost_estimate: Optional[float] = None
    created_at: datetime
    evaluations: List[EvaluationResultResponse] = []
    logs: List[ExecutionLogItem] = []

    model_config = ConfigDict(from_attributes=True)

