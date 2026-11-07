"""Pydantic schemas for Evaluations and Metric Results."""
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field
from app.models.enums import MetricStatus


class MetricEvaluationResult(BaseModel):
    """Output contract for a single evaluation metric."""
    metric_name: str
    score: float
    score_min: float = 0.0
    score_max: float = 1.0
    explanation: str
    status: MetricStatus = MetricStatus.PASS
    metadata: Dict[str, Any] = {}


class EvaluationRunRequest(BaseModel):
    """Ad-hoc evaluation request."""
    question: str
    generated_answer: str
    reference_answer: Optional[str] = None
    contexts: Optional[List[str]] = None
    metrics: Optional[List[str]] = None


class EvaluationResultResponse(BaseModel):
    id: Optional[int] = None
    execution_id: Optional[int] = None
    overall_score: float
    summary: str
    status: MetricStatus
    metrics: List[MetricEvaluationResult]
    metadata: Dict[str, Any] = {}
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class RAGEvaluationRequest(BaseModel):
    """Dedicated RAG Triad evaluation request."""
    question: str
    retrieved_contexts: List[str]
    generated_answer: str
    reference_answer: Optional[str] = None


class RAGTriadScores(BaseModel):
    context_relevance: float
    faithfulness: float
    answer_relevance: float
    context_coverage: float
    overall_rag_score: float


class RAGEvaluationResponse(BaseModel):
    triad_scores: RAGTriadScores
    hallucination_detected: bool
    hallucination_risk_score: float
    details: List[MetricEvaluationResult]
    explanation: str

