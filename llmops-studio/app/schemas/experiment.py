"""Pydantic schemas for Experiment definitions, execution requests, and results."""
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field
from app.models.enums import ExperimentStatus
from app.schemas.provider import GenerationParameters


class ExperimentCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=150)
    description: Optional[str] = None
    dataset_id: int
    prompt_version_id: int
    selected_model_ids: List[int] = Field(..., min_length=1)
    generation_parameters: Optional[GenerationParameters] = None
    evaluation_metric_names: Optional[List[str]] = Field(
        default=["exact_match", "semantic_similarity", "answer_relevance", "faithfulness", "completeness"]
    )


class ExperimentRunResponse(BaseModel):
    id: int
    experiment_id: int
    model_config_id: int
    model_identifier: str
    display_name: str
    status: ExperimentStatus
    run_index: int
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    latency_ms: Optional[float] = None
    error_message: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ExperimentResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    dataset_id: int
    prompt_version_id: int
    status: ExperimentStatus
    total_runs: int
    completed_runs: int
    failed_runs: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ExperimentDetailResponse(ExperimentResponse):
    dataset_name: Optional[str] = None
    prompt_name: Optional[str] = None
    runs: List[ExperimentRunResponse] = []


class ExperimentExecutionItem(BaseModel):
    execution_id: int
    request_id: str
    model_identifier: str
    model_name: str
    question: str
    output_text: Optional[str] = None
    latency_ms: float
    total_tokens: int
    status: str
    evaluation_score: Optional[float] = None
    metrics: Dict[str, float] = {}


class ExperimentResultsResponse(BaseModel):
    experiment_id: int
    experiment_name: str
    status: str
    total_executions: int
    model_summaries: Dict[str, Dict[str, Any]]
    executions: List[ExperimentExecutionItem]

