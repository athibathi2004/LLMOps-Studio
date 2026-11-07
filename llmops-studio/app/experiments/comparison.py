"""Model Comparison Engine across evaluation metrics, latency, tokens, and cost."""
import statistics
from typing import Any, Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.enums import ExecutionStatus
from app.models.models import (
    DatasetRecord,
    EvaluationMetric,
    EvaluationResult,
    Experiment,
    ModelConfiguration,
    ModelExecution,
)
from app.observability.metrics import calculate_percentiles
from app.schemas.analytics import ModelComparisonItem, ModelComparisonResponse


class ModelComparisonEngine:
    """Aggregates and formats multi-model comparison benchmarks."""

    @staticmethod
    async def compare_experiment_models(
        session: AsyncSession, experiment_id: int
    ) -> ModelComparisonResponse:
        """Compute side-by-side comparative metrics for all models in an experiment."""
        stmt = (
            select(ModelExecution)
            .where(ModelExecution.experiment_id == experiment_id)
            .options(
                selectinload(ModelExecution.model_config).selectinload(ModelConfiguration.provider),
                selectinload(ModelExecution.evaluation_results).selectinload(EvaluationResult.metrics),
                selectinload(ModelExecution.dataset_record),
            )
        )
        executions = list((await session.execute(stmt)).scalars().all())

        # Group executions by model_config_id
        grouped: Dict[int, List[ModelExecution]] = {}
        for ex in executions:
            grouped.setdefault(ex.model_config_id, []).append(ex)

        items: List[ModelComparisonItem] = []

        for model_id, model_execs in grouped.items():
            if not model_execs:
                continue

            model_cfg = model_execs[0].model_config
            total_runs = len(model_execs)
            success_runs = sum(1 for e in model_execs if e.status == ExecutionStatus.SUCCESS)
            success_rate = round((success_runs / max(1, total_runs)) * 100, 2)

            latencies = [e.latency_ms for e in model_execs]
            pcts = calculate_percentiles(latencies)

            tokens = [e.total_tokens for e in model_execs]
            avg_tokens = round(statistics.mean(tokens), 1) if tokens else 0.0

            # Evaluation scores
            all_scores: List[float] = []
            metric_buckets: Dict[str, List[float]] = {}

            for e in model_execs:
                for eval_res in e.evaluation_results:
                    all_scores.append(eval_res.overall_score)
                    for m in eval_res.metrics:
                        metric_buckets.setdefault(m.metric_name, []).append(m.score)

            avg_overall_score = round(statistics.mean(all_scores), 3) if all_scores else 0.0

            metric_breakdown = {
                m_name: round(statistics.mean(scores), 3)
                for m_name, scores in metric_buckets.items()
            }

            # Cost calculation (Strict requirement: Never invent provider pricing)
            cost_configured = (
                model_cfg.cost_per_1k_input_tokens is not None
                and model_cfg.cost_per_1k_output_tokens is not None
            )

            if cost_configured:
                # Compute average cost per query
                total_cost = sum(e.cost_estimate for e in model_execs if e.cost_estimate is not None)
                avg_cost = round(total_cost / max(1, total_runs), 6)
                cost_note = f"Calculated based on ${model_cfg.cost_per_1k_input_tokens}/1k in, ${model_cfg.cost_per_1k_output_tokens}/1k out."
            else:
                avg_cost = None
                cost_note = "Cost unavailable: pricing not configured for this model configuration."

            item = ModelComparisonItem(
                model_id=model_cfg.id,
                model_identifier=model_cfg.model_identifier,
                display_name=model_cfg.display_name,
                provider=model_cfg.provider.name,
                total_runs=total_runs,
                success_rate=success_rate,
                avg_latency_ms=pcts["mean"],
                p95_latency_ms=pcts["p95"],
                avg_tokens=avg_tokens,
                avg_evaluation_score=avg_overall_score,
                metric_breakdown=metric_breakdown,
                cost_per_query=avg_cost,
                cost_available=cost_configured,
                cost_note=cost_note,
            )
            items.append(item)

        # Collect side-by-side test case examples
        # Map record_id -> {model_name: output_text}
        sample_dict: Dict[int, Dict[str, Any]] = {}
        for ex in executions:
            if not ex.dataset_record_id:
                continue
            rec_id = ex.dataset_record_id
            if rec_id not in sample_dict:
                question = ex.dataset_record.question if ex.dataset_record else "Question"
                ref_ans = ex.dataset_record.reference_answer if ex.dataset_record else None
                sample_dict[rec_id] = {
                    "record_id": rec_id,
                    "question": question,
                    "reference_answer": ref_ans,
                    "model_outputs": {},
                }
            sample_dict[rec_id]["model_outputs"][ex.model_config.display_name] = {
                "output_text": ex.output_text,
                "latency_ms": ex.latency_ms,
                "total_tokens": ex.total_tokens,
                "status": ex.status.value,
            }

        samples = list(sample_dict.values())[:10]

        return ModelComparisonResponse(
            experiment_id=experiment_id,
            models=items,
            side_by_side_samples=samples,
        )


model_comparison_engine = ModelComparisonEngine()

