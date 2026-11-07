"""Execution traces and observability telemetry endpoints."""
import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.models.enums import ErrorCategory, ExecutionStatus
from app.models.models import EvaluationResult, ExecutionLog, ModelConfiguration, ModelExecution
from app.schemas.evaluation import EvaluationResultResponse, MetricEvaluationResult
from app.schemas.execution import (
    ExecutionLogItem,
    ModelExecutionDetail,
    ModelExecutionSummary,
)

router = APIRouter()


@router.get("", response_model=List[ModelExecutionSummary], summary="List execution traces with filtering")
async def list_executions(
    model_id: Optional[int] = Query(None, description="Filter by model ID"),
    status: Optional[ExecutionStatus] = Query(None, description="Filter by execution status"),
    error_category: Optional[ErrorCategory] = Query(None, description="Filter by error category"),
    experiment_id: Optional[int] = Query(None, description="Filter by experiment ID"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve chronological model execution telemetry traces."""
    stmt = (
        select(ModelExecution)
        .options(selectinload(ModelExecution.model_config))
        .order_by(ModelExecution.created_at.desc())
    )

    if model_id is not None:
        stmt = stmt.where(ModelExecution.model_config_id == model_id)
    if status is not None:
        stmt = stmt.where(ModelExecution.status == status)
    if error_category is not None:
        stmt = stmt.where(ModelExecution.error_category == error_category)
    if experiment_id is not None:
        stmt = stmt.where(ModelExecution.experiment_id == experiment_id)

    stmt = stmt.offset(offset).limit(limit)
    res = await db.execute(stmt)
    executions = res.scalars().all()

    output = []
    for e in executions:
        output.append(
            ModelExecutionSummary(
                id=e.id,
                request_id=e.request_id,
                model_identifier=e.model_config.model_identifier,
                model_name=e.model_config.display_name,
                status=e.status,
                error_category=e.error_category,
                latency_ms=e.latency_ms,
                total_tokens=e.total_tokens,
                cost_estimate=e.cost_estimate,
                created_at=e.created_at,
            )
        )
    return output


@router.get("/{execution_id}", response_model=ModelExecutionDetail, summary="Get full execution trace by ID")
async def get_execution(
    execution_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Retrieve full request-response telemetry trace, evaluation metrics, and audit logs."""
    stmt = (
        select(ModelExecution)
        .where(ModelExecution.id == execution_id)
        .options(
            selectinload(ModelExecution.model_config).selectinload(ModelConfiguration.provider),
            selectinload(ModelExecution.evaluation_results).selectinload(EvaluationResult.metrics),
            selectinload(ModelExecution.logs),
        )
    )
    execution = (await db.execute(stmt)).scalar_one_or_none()
    if not execution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ModelExecution with ID {execution_id} not found.",
        )

    # Format evaluation results
    evals_resp: List[EvaluationResultResponse] = []
    for ev in execution.evaluation_results:
        metrics_resp = [
            MetricEvaluationResult(
                metric_name=m.metric_name,
                score=m.score,
                score_min=m.score_min,
                score_max=m.score_max,
                explanation=m.explanation or "",
                status=m.status,
            )
            for m in ev.metrics
        ]
        evals_resp.append(
            EvaluationResultResponse(
                id=ev.id,
                execution_id=ev.execution_id,
                overall_score=ev.overall_score,
                summary=ev.summary or "",
                status=ev.status,
                metrics=metrics_resp,
                created_at=ev.created_at,
            )
        )

    # Format logs
    logs_resp = [
        ExecutionLogItem(
            timestamp=l.timestamp,
            level=l.level,
            message=l.message,
            metadata=json.loads(l.metadata_json) if l.metadata_json else {},
        )
        for l in execution.logs
    ]

    gen_params = (
        json.loads(execution.generation_parameters)
        if execution.generation_parameters
        else {}
    )

    return ModelExecutionDetail(
        id=execution.id,
        request_id=execution.request_id,
        experiment_id=execution.experiment_id,
        experiment_run_id=execution.experiment_run_id,
        model_config_id=execution.model_config_id,
        model_identifier=execution.model_config.model_identifier,
        model_name=execution.model_config.display_name,
        provider_name=execution.model_config.provider.name,
        input_prompt=execution.input_prompt,
        output_text=execution.output_text,
        status=execution.status,
        error_category=execution.error_category,
        error_details=execution.error_details,
        start_time=execution.start_time,
        end_time=execution.end_time,
        latency_ms=execution.latency_ms,
        input_tokens=execution.input_tokens,
        output_tokens=execution.output_tokens,
        total_tokens=execution.total_tokens,
        generation_parameters=gen_params,
        cost_estimate=execution.cost_estimate,
        created_at=execution.created_at,
        evaluations=evals_resp,
        logs=logs_resp,
    )

