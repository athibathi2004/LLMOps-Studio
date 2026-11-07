"""Tests for Analytics service aggregations and failure diagnostics."""
from datetime import datetime, timezone
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.service import analytics_service
from app.models.enums import ErrorCategory, ExecutionStatus
from app.models.models import ModelConfiguration
from app.observability.tracker import ExecutionTracker


@pytest.mark.asyncio
async def test_analytics_overview_and_models(db_session: AsyncSession):
    """Verify overview KPIs and model metric summaries."""
    overview = await analytics_service.get_overview(db_session)
    assert overview.total_experiments >= 0
    assert overview.total_executions >= 0
    assert 0.0 <= overview.success_rate_percent <= 100.0
    assert overview.active_models_count >= 1

    model_metrics = await analytics_service.get_model_metrics(db_session)
    assert len(model_metrics) >= 1
    for m in model_metrics:
        assert m.display_name != ""
        assert m.provider != ""


@pytest.mark.asyncio
async def test_failure_analytics_categorization(db_session: AsyncSession):
    """Verify recording failures and aggregating breakdown by category."""
    stmt = select(ModelConfiguration).where(ModelConfiguration.model_identifier == "mock-deterministic")
    model_cfg = (await db_session.execute(stmt)).scalars().first()
    assert model_cfg is not None

    tracker = ExecutionTracker(db_session)
    now = datetime.now(timezone.utc)

    # Record intentional timeout failure
    await tracker.record_execution(
        model_config=model_cfg,
        input_prompt="Failure test",
        output_text="",
        status=ExecutionStatus.TIMEOUT,
        start_time=now,
        end_time=now,
        latency_ms=30000.0,
        input_tokens=10,
        output_tokens=0,
        error_category=ErrorCategory.TIMEOUT,
        error_details="Execution timed out",
    )

    failures = await analytics_service.get_failure_analytics(db_session)
    assert failures.total_failures >= 1
    assert failures.overall_failure_rate >= 0.0
    categories = [cat.category for cat in failures.breakdown_by_category]
    assert "TIMEOUT" in categories
    assert len(failures.recent_failures) >= 1

