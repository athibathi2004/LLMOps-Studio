"""Tests for Observability tracking, telemetry percentiles, and error categorization."""
from datetime import datetime, timezone
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import ErrorCategory, ExecutionStatus
from app.models.models import ModelConfiguration
from app.observability.logging import ExecutionLogger
from app.observability.metrics import calculate_percentiles, estimate_token_count
from app.observability.tracker import ExecutionTracker


def test_percentile_calculations():
    """Verify statistical percentile helper."""
    series = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0]
    pcts = calculate_percentiles(series)
    assert pcts["p50"] == 55.0
    assert pcts["p95"] == 100.0
    assert pcts["mean"] == 55.0


def test_error_categorization():
    """Verify mapping of raw exceptions to error categories."""
    tracker = ExecutionTracker(None)

    assert tracker.categorize_error(TimeoutError("Operation timed out")) == ErrorCategory.TIMEOUT
    assert tracker.categorize_error(ConnectionError("Connection refused by host")) == ErrorCategory.PROVIDER_UNAVAILABLE
    assert tracker.categorize_error(ValueError("Output was empty string")) == ErrorCategory.EMPTY_RESPONSE
    assert tracker.categorize_error(TypeError("Unclosed JSON structure")) == ErrorCategory.MALFORMED_OUTPUT


@pytest.mark.asyncio
async def test_execution_tracker_persistence(db_session: AsyncSession):
    """Verify recording model execution and logging trace."""
    stmt = select(ModelConfiguration).where(ModelConfiguration.model_identifier == "mock-deterministic")
    model_cfg = (await db_session.execute(stmt)).scalars().first()
    assert model_cfg is not None

    tracker = ExecutionTracker(db_session)
    start_time = datetime.now(timezone.utc)
    end_time = datetime.now(timezone.utc)

    execution = await tracker.record_execution(
        model_config=model_cfg,
        input_prompt="Test prompt",
        output_text="Test output",
        status=ExecutionStatus.SUCCESS,
        start_time=start_time,
        end_time=end_time,
        latency_ms=25.4,
        input_tokens=10,
        output_tokens=12,
    )

    assert execution.id is not None
    assert execution.request_id != ""
    assert execution.total_tokens == 22
    assert execution.status == ExecutionStatus.SUCCESS

    # Test audit logging
    log = await ExecutionLogger.log_event(
        session=db_session,
        execution_id=execution.id,
        level="INFO",
        message="Test event log",
    )
    assert log.id is not None
    logs = await ExecutionLogger.get_logs_for_execution(db_session, execution.id)
    assert len(logs) >= 1

