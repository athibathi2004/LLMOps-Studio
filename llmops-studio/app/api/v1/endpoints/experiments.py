"""Experiment definition, runner, and results endpoints."""
import json
import statistics
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.experiments.comparison import model_comparison_engine
from app.experiments.manager import ExperimentManager
from app.experiments.runner import ExperimentRunner
from app.models.models import (
    EvaluationResult,
    Experiment,
    ExperimentRun,
    ModelConfiguration,
    ModelExecution,
)
from app.schemas.analytics import ModelComparisonResponse
from app.schemas.experiment import (
    ExperimentCreate,
    ExperimentDetailResponse,
    ExperimentExecutionItem,
    ExperimentResponse,
    ExperimentResultsResponse,
    ExperimentRunResponse,
)

router = APIRouter()


@router.post("", response_model=ExperimentResponse, status_code=status.HTTP_201_CREATED, summary="Create a new multi-model evaluation experiment")
async def create_experiment(
    payload: ExperimentCreate,
    db: AsyncSession = Depends(get_db),
):
    """Define a new experiment with prompt version, dataset, and models to compare."""
    try:
        experiment = await ExperimentManager.create_experiment(db, payload)
        return ExperimentResponse.model_validate(experiment)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get("", response_model=List[ExperimentResponse], summary="List all experiments")
async def list_experiments(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve all evaluation experiments ordered by creation date."""
    experiments = await ExperimentManager.list_experiments(db, limit=limit, offset=offset)
    return [ExperimentResponse.model_validate(e) for e in experiments]


@router.get("/{experiment_id}", response_model=ExperimentDetailResponse, summary="Get experiment definition and run states")
async def get_experiment(
    experiment_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Fetch complete experiment details including all sub-runs."""
    experiment = await ExperimentManager.get_experiment(db, experiment_id)
    if not experiment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Experiment with ID {experiment_id} not found.",
        )

    runs_resp = [
        ExperimentRunResponse(
            id=r.id,
            experiment_id=r.experiment_id,
            model_config_id=r.model_config_id,
            model_identifier=r.model_config.model_identifier,
            display_name=r.model_config.display_name,
            status=r.status,
            run_index=r.run_index,
            started_at=r.started_at,
            completed_at=r.completed_at,
            latency_ms=r.latency_ms,
            error_message=r.error_message,
        )
        for r in experiment.runs
    ]

    return ExperimentDetailResponse(
        id=experiment.id,
        name=experiment.name,
        description=experiment.description,
        dataset_id=experiment.dataset_id,
        dataset_name=experiment.dataset.name if experiment.dataset else None,
        prompt_version_id=experiment.prompt_version_id,
        prompt_name=experiment.prompt_version.prompt.name if (experiment.prompt_version and experiment.prompt_version.prompt) else None,
        status=experiment.status,
        total_runs=experiment.total_runs,
        completed_runs=experiment.completed_runs,
        failed_runs=experiment.failed_runs,
        created_at=experiment.created_at,
        updated_at=experiment.updated_at,
        runs=runs_resp,
    )


@router.post("/{experiment_id}/run", response_model=ExperimentResponse, summary="Execute an experiment across all models and test cases")
async def run_experiment(
    experiment_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Trigger asynchronous execution of the experiment across all designated models."""
    try:
        experiment = await ExperimentRunner.run_experiment(db, experiment_id)
        return ExperimentResponse.model_validate(experiment)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get("/{experiment_id}/results", response_model=ExperimentResultsResponse, summary="Get full experiment execution traces and metric results")
async def get_experiment_results(
    experiment_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Retrieve full evaluation outputs and aggregate statistics for an experiment."""
    experiment = await db.get(Experiment, experiment_id)
    if not experiment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Experiment with ID {experiment_id} not found.",
        )

    stmt = (
        select(ModelExecution)
        .where(ModelExecution.experiment_id == experiment_id)
        .options(
            selectinload(ModelExecution.model_config),
            selectinload(ModelExecution.evaluation_results).selectinload(EvaluationResult.metrics),
            selectinload(ModelExecution.dataset_record),
        )
        .order_by(ModelExecution.created_at.asc())
    )
    executions = list((await db.execute(stmt)).scalars().all())

    # Aggregate summaries by model
    model_summaries: Dict[str, Dict[str, Any]] = {}
    exec_items: List[ExperimentExecutionItem] = []

    for ex in executions:
        m_name = ex.model_config.display_name
        if m_name not in model_summaries:
            model_summaries[m_name] = {
                "total_runs": 0,
                "success_runs": 0,
                "latencies": [],
                "tokens": [],
                "scores": [],
            }

        s = model_summaries[m_name]
        s["total_runs"] += 1
        if ex.status.value == "SUCCESS":
            s["success_runs"] += 1
        s["latencies"].append(ex.latency_ms)
        s["tokens"].append(ex.total_tokens)

        # Evaluations
        score_val = None
        metrics_dict = {}
        if ex.evaluation_results:
            latest_eval = ex.evaluation_results[0]
            score_val = latest_eval.overall_score
            s["scores"].append(score_val)
            for m in latest_eval.metrics:
                metrics_dict[m.metric_name] = m.score

        q_text = ex.dataset_record.question if ex.dataset_record else "Prompt Test"

        exec_items.append(
            ExperimentExecutionItem(
                execution_id=ex.id,
                request_id=ex.request_id,
                model_identifier=ex.model_config.model_identifier,
                model_name=m_name,
                question=q_text,
                output_text=ex.output_text,
                latency_ms=ex.latency_ms,
                total_tokens=ex.total_tokens,
                status=ex.status.value,
                evaluation_score=score_val,
                metrics=metrics_dict,
            )
        )

    # Formatted summaries
    formatted_summaries: Dict[str, Dict[str, Any]] = {}
    for m_name, s in model_summaries.items():
        avg_score = round(statistics.mean(s["scores"]), 3) if s["scores"] else 0.0
        avg_lat = round(statistics.mean(s["latencies"]), 1) if s["latencies"] else 0.0
        avg_tok = round(statistics.mean(s["tokens"]), 1) if s["tokens"] else 0.0
        formatted_summaries[m_name] = {
            "total_runs": s["total_runs"],
            "success_rate": round((s["success_runs"] / max(1, s["total_runs"])) * 100, 1),
            "average_score": avg_score,
            "average_latency_ms": avg_lat,
            "average_tokens": avg_tok,
        }

    return ExperimentResultsResponse(
        experiment_id=experiment.id,
        experiment_name=experiment.name,
        status=experiment.status.value,
        total_executions=len(executions),
        model_summaries=formatted_summaries,
        executions=exec_items,
    )


@router.get("/{experiment_id}/comparison", response_model=ModelComparisonResponse, summary="Compare experiment models side-by-side")
async def get_experiment_comparison(
    experiment_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Retrieve side-by-side performance, quality, and cost benchmarks for an experiment."""
    experiment = await db.get(Experiment, experiment_id)
    if not experiment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Experiment with ID {experiment_id} not found.",
        )

    return await model_comparison_engine.compare_experiment_models(db, experiment_id)

