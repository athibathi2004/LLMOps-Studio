"""Pydantic schemas for Analytics, Metrics trends, and Model Comparisons."""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class AnalyticsOverviewResponse(BaseModel):
    total_experiments: int
    total_executions: int
    success_rate_percent: float
    average_score: float
    average_latency_ms: float
    total_tokens_consumed: int
    failure_count: int
    active_models_count: int


class ModelMetricSummary(BaseModel):
    model_id: int
    model_identifier: str
    display_name: str
    provider: str
    total_executions: int
    success_rate: float
    average_latency_ms: float
    p95_latency_ms: float
    average_tokens: float
    average_score: float
    total_cost: Optional[float] = None
    cost_available: bool = False


class PerformanceAnalyticsResponse(BaseModel):
    latency_trend: List[Dict[str, Any]]
    score_distribution: Dict[str, int]
    token_usage_by_model: Dict[str, int]
    execution_volume_timeline: List[Dict[str, Any]]


class FailureCategoryCount(BaseModel):
    category: str
    count: int
    percentage: float


class FailureAnalyticsResponse(BaseModel):
    total_failures: int
    overall_failure_rate: float
    breakdown_by_category: List[FailureCategoryCount]
    failures_by_model: Dict[str, int]
    recent_failures: List[Dict[str, Any]]


class ModelComparisonItem(BaseModel):
    model_id: int
    model_identifier: str
    display_name: str
    provider: str
    total_runs: int
    success_rate: float
    avg_latency_ms: float
    p95_latency_ms: float
    avg_tokens: float
    avg_evaluation_score: float
    metric_breakdown: Dict[str, float]
    cost_per_query: Optional[float] = None
    cost_available: bool = False
    cost_note: str


class ModelComparisonResponse(BaseModel):
    experiment_id: Optional[int] = None
    models: List[ModelComparisonItem]
    side_by_side_samples: List[Dict[str, Any]]

