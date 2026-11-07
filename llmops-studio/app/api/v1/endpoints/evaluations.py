"""Evaluation endpoints for ad-hoc scoring and RAG Triad assessments."""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.evaluation.engine import evaluation_engine
from app.evaluation.rag_evaluator import rag_evaluator
from app.models.models import EvaluationResult
from app.schemas.evaluation import (
    EvaluationResultResponse,
    EvaluationRunRequest,
    MetricEvaluationResult,
    RAGEvaluationRequest,
    RAGEvaluationResponse,
)

router = APIRouter()


@router.post("/run", response_model=EvaluationResultResponse, summary="Run ad-hoc evaluation metrics on input text")
async def run_evaluation(
    payload: EvaluationRunRequest,
):
    """
    Execute modular evaluation metrics (Exact Match, Semantic Similarity, Answer Relevance,
    Context Relevance, Faithfulness, Response Completeness, Hallucination Risk).
    """
    if not payload.generated_answer:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="generated_answer cannot be empty.",
        )

    return evaluation_engine.evaluate(
        generated_answer=payload.generated_answer,
        question=payload.question,
        reference_answer=payload.reference_answer,
        contexts=payload.contexts,
        selected_metrics=payload.metrics,
    )


@router.post("/rag", response_model=RAGEvaluationResponse, summary="Execute dedicated RAG Triad pipeline evaluation")
async def run_rag_evaluation(
    payload: RAGEvaluationRequest,
):
    """
    Run the canonical RAG Triad evaluation:
    1. Context Relevance
    2. Groundedness / Faithfulness
    3. Answer Relevance
    Plus Context Coverage and Hallucination Risk Indicators.
    """
    if not payload.retrieved_contexts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="retrieved_contexts array cannot be empty for RAG evaluation.",
        )

    return rag_evaluator.evaluate_pipeline(payload)


@router.get("/{evaluation_id}", response_model=EvaluationResultResponse, summary="Get stored evaluation result by ID")
async def get_evaluation(
    evaluation_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Retrieve persisted evaluation record and breakdown of individual metric scores."""
    stmt = (
        select(EvaluationResult)
        .where(EvaluationResult.id == evaluation_id)
        .options(selectinload(EvaluationResult.metrics))
    )
    result = (await db.execute(stmt)).scalar_one_or_none()
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"EvaluationResult with ID {evaluation_id} not found.",
        )

    metrics_resp = [
        MetricEvaluationResult(
            metric_name=m.metric_name,
            score=m.score,
            score_min=m.score_min,
            score_max=m.score_max,
            explanation=m.explanation or "",
            status=m.status,
        )
        for m in result.metrics
    ]

    return EvaluationResultResponse(
        id=result.id,
        execution_id=result.execution_id,
        overall_score=result.overall_score,
        summary=result.summary or "",
        status=result.status,
        metrics=metrics_resp,
        created_at=result.created_at,
    )

