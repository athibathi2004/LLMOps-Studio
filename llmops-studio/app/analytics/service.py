"""Analytics service for system overview, model performance, and failure categorization."""
import statistics
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.enums import ErrorCategory, ExecutionStatus
from app.models.models import (
    EvaluationResult,
    Experiment,
    ModelConfiguration,
    ModelExecution,
)
from app.observability.metrics import calculate_percentiles
from app.schemas.analytics import (
    AnalyticsOverviewResponse,
    FailureAnalyticsResponse,
    FailureCategoryCount,
    ModelMetricSummary,
    PerformanceAnalyticsResponse,
)


class AnalyticsService:
    """Computes global aggregations, model metrics, and failure diagnostics."""

    @staticmethod
    async def get_overview(session: AsyncSession) -> AnalyticsOverviewResponse:
        """Compute high-level KPIs for dashboard overview."""
        # Total experiments
        total_exp = (
            await session.execute(select(func.count(Experiment.id)))
        ).scalar() or 0

        # Total executions
        total_exec = (
            await session.execute(select(func.count(ModelExecution.id)))
        ).scalar() or 0

        # Successes & Failures
        success_exec = (
            await session.execute(
                select(func.count(ModelExecution.id)).where(
                    ModelExecution.status == ExecutionStatus.SUCCESS
                )
            )
        ).scalar() or 0
        failure_exec = total_exec - success_exec
        success_rate = (
            round((success_exec / max(1, total_exec)) * 100, 2)
            if total_exec > 0
            else 100.0
        )

        # Average latency & total tokens
        exec_stats = (
            await session.execute(
                select(
                    func.avg(ModelExecution.latency_ms),
                    func.sum(ModelExecution.total_tokens),
                )
            )
        ).first()

        avg_latency = round(float(exec_stats[0] or 0.0), 2)
        total_tokens = int(exec_stats[1] or 0)

        # Average evaluation score
        avg_score_res = (
            await session.execute(select(func.avg(EvaluationResult.overall_score)))
        ).scalar()
        avg_score = round(float(avg_score_res or 0.0), 3)

        # Active models count
        active_models = (
            await session.execute(
                select(func.count(ModelConfiguration.id)).where(
                    ModelConfiguration.is_available.is_(True)
                )
            )
        ).scalar() or 0

        return AnalyticsOverviewResponse(
            total_experiments=total_exp,
            total_executions=total_exec,
            success_rate_percent=success_rate,
            average_score=avg_score,
            average_latency_ms=avg_latency,
            total_tokens_consumed=total_tokens,
            failure_count=failure_exec,
            active_models_count=active_models,
        )

    @staticmethod
    async def get_model_metrics(session: AsyncSession) -> List[ModelMetricSummary]:
        """Aggregate performance and quality benchmarks per registered model."""
        stmt = (
            select(ModelConfiguration)
            .options(
                selectinload(ModelConfiguration.provider),
                selectinload(ModelConfiguration.executions).selectinload(
                    ModelExecution.evaluation_results
                ),
            )
        )
        models = list((await session.execute(stmt)).scalars().all())

        summaries: List[ModelMetricSummary] = []

        for m in models:
            execs = m.executions
            total = len(execs)
            if total == 0:
                cost_avail = (
                    m.cost_per_1k_input_tokens is not None
                    and m.cost_per_1k_output_tokens is not None
                )
                summaries.append(
                    ModelMetricSummary(
                        model_id=m.id,
                        model_identifier=m.model_identifier,
                        display_name=m.display_name,
                        provider=m.provider.name,
                        total_executions=0,
                        success_rate=100.0,
                        average_latency_ms=0.0,
                        p95_latency_ms=0.0,
                        average_tokens=0.0,
                        average_score=0.0,
                        total_cost=0.0 if cost_avail else None,
                        cost_available=cost_avail,
                    )
                )
                continue

            successes = sum(1 for e in execs if e.status == ExecutionStatus.SUCCESS)
            success_rate = round((successes / total) * 100, 2)

            latencies = [e.latency_ms for e in execs]
            pcts = calculate_percentiles(latencies)

            tokens = [e.total_tokens for e in execs]
            avg_tokens = round(statistics.mean(tokens), 1)

            scores = []
            for e in execs:
                for ev in e.evaluation_results:
                    scores.append(ev.overall_score)
            avg_score = round(statistics.mean(scores), 3) if scores else 0.0

            cost_avail = (
                m.cost_per_1k_input_tokens is not None
                and m.cost_per_1k_output_tokens is not None
            )
            total_cost = None
            if cost_avail:
                total_cost = round(
                    sum(e.cost_estimate for e in execs if e.cost_estimate is not None),
                    6,
                )

            summaries.append(
                ModelMetricSummary(
                    model_id=m.id,
                    model_identifier=m.model_identifier,
                    display_name=m.display_name,
                    provider=m.provider.name,
                    total_executions=total,
                    success_rate=success_rate,
                    average_latency_ms=pcts["mean"],
                    p95_latency_ms=pcts["p95"],
                    average_tokens=avg_tokens,
                    average_score=avg_score,
                    total_cost=total_cost,
                    cost_available=cost_avail,
                )
            )

        # Sort by total executions and average score
        summaries.sort(key=lambda s: (s.total_executions, s.average_score), reverse=True)
        return summaries

    @staticmethod
    async def get_performance_trends(session: AsyncSession) -> PerformanceAnalyticsResponse:
        """Compute score distributions, latency series, and token consumption charts."""
        stmt = (
            select(ModelExecution)
            .options(
                selectinload(ModelExecution.model_config),
                selectinload(ModelExecution.evaluation_results),
            )
            .order_by(ModelExecution.created_at.desc())
            .limit(200)
        )
        execs = list((await session.execute(stmt)).scalars().all())

        # Score distribution histogram (0.0 to 1.0 in 5 buckets)
        score_buckets = {
            "0.0 - 0.2": 0,
            "0.2 - 0.4": 0,
            "0.4 - 0.6": 0,
            "0.6 - 0.8": 0,
            "0.8 - 1.0": 0,
        }

        # Token usage by model
        tokens_by_model: Dict[str, int] = {}
        # Latency trend (last 30 chronological executions)
        latency_trend: List[Dict[str, Any]] = []

        # Chronological order for trend charts
        chronological = list(reversed(execs))

        for ex in chronological:
            m_name = ex.model_config.display_name
            tokens_by_model[m_name] = tokens_by_model.get(m_name, 0) + ex.total_tokens

            latency_trend.append({
                "timestamp": ex.created_at.strftime("%H:%M:%S"),
                "model": m_name,
                "latency_ms": ex.latency_ms,
                "status": ex.status.value,
            })

            for ev in ex.evaluation_results:
                sc = ev.overall_score
                if sc < 0.2:
                    score_buckets["0.0 - 0.2"] += 1
                elif sc < 0.4:
                    score_buckets["0.2 - 0.4"] += 1
                elif sc < 0.6:
                    score_buckets["0.4 - 0.6"] += 1
                elif sc < 0.8:
                    score_buckets["0.6 - 0.8"] += 1
                else:
                    score_buckets["0.8 - 1.0"] += 1

        # Execution volume grouped by day or hour
        volume_map: Dict[str, int] = {}
        for ex in execs:
            day_str = ex.created_at.strftime("%Y-%m-%d")
            volume_map[day_str] = volume_map.get(day_str, 0) + 1

        volume_timeline = [
            {"date": k, "count": v}
            for k, v in sorted(volume_map.items())
        ]

        return PerformanceAnalyticsResponse(
            latency_trend=latency_trend[-40:],
            score_distribution=score_buckets,
            token_usage_by_model=tokens_by_model,
            execution_volume_timeline=volume_timeline,
        )

    @staticmethod
    async def get_failure_analytics(session: AsyncSession) -> FailureAnalyticsResponse:
        """Provide detailed root cause breakdown and failure diagnostics."""
        stmt = (
            select(ModelExecution)
            .where(ModelExecution.status != ExecutionStatus.SUCCESS)
            .options(selectinload(ModelExecution.model_config))
            .order_by(ModelExecution.created_at.desc())
        )
        failed_execs = list((await session.execute(stmt)).scalars().all())

        total_execs = (
            await session.execute(select(func.count(ModelExecution.id)))
        ).scalar() or 0

        total_failures = len(failed_execs)
        failure_rate = (
            round((total_failures / max(1, total_execs)) * 100, 2)
            if total_execs > 0
            else 0.0
        )

        category_counts: Dict[str, int] = {}
        model_failures: Dict[str, int] = {}

        for ex in failed_execs:
            cat_name = ex.error_category.value
            category_counts[cat_name] = category_counts.get(cat_name, 0) + 1

            m_name = ex.model_config.display_name
            model_failures[m_name] = model_failures.get(m_name, 0) + 1

        breakdown = [
            FailureCategoryCount(
                category=cat,
                count=cnt,
                percentage=round((cnt / max(1, total_failures)) * 100, 2),
            )
            for cat, cnt in sorted(category_counts.items(), key=lambda x: x[1], reverse=True)
        ]

        recent = [
            {
                "id": ex.id,
                "request_id": ex.request_id,
                "model": ex.model_config.display_name,
                "category": ex.error_category.value,
                "error_details": ex.error_details,
                "timestamp": ex.created_at.isoformat(),
            }
            for ex in failed_execs[:15]
        ]

        return FailureAnalyticsResponse(
            total_failures=total_failures,
            overall_failure_rate=failure_rate,
            breakdown_by_category=breakdown,
            failures_by_model=model_failures,
            recent_failures=recent,
        )


analytics_service = AnalyticsService()

