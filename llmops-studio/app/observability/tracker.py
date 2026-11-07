"""Execution Tracking and Observability Engine."""
import json
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import ErrorCategory, ExecutionStatus
from app.models.models import ExecutionLog, ModelConfiguration, ModelExecution


class ExecutionTracker:
    """Manages telemetry recording, error categorization, and lifecycle logs for every model execution."""

    def __init__(self, session: AsyncSession):
        self.session = session

    @staticmethod
    def categorize_error(error: Exception) -> ErrorCategory:
        """Map standard Python exceptions to standardized domain error categories."""
        msg = str(error).lower()
        if "timeout" in msg or "timed out" in msg:
            return ErrorCategory.TIMEOUT
        if "connect" in msg or "connection refused" in msg or "503" in msg or "unreachable" in msg:
            return ErrorCategory.PROVIDER_UNAVAILABLE
        if "empty" in msg:
            return ErrorCategory.EMPTY_RESPONSE
        if "json" in msg or "malformed" in msg or "parse" in msg:
            return ErrorCategory.MALFORMED_OUTPUT
        if "config" in msg or "not found" in msg:
            return ErrorCategory.CONFIGURATION_ERROR
        return ErrorCategory.UNKNOWN

    async def record_execution(
        self,
        model_config: ModelConfiguration,
        input_prompt: str,
        output_text: Optional[str],
        status: ExecutionStatus,
        start_time: datetime,
        end_time: datetime,
        latency_ms: float,
        input_tokens: int,
        output_tokens: int,
        error_category: ErrorCategory = ErrorCategory.NONE,
        error_details: Optional[str] = None,
        experiment_id: Optional[int] = None,
        experiment_run_id: Optional[int] = None,
        prompt_version_id: Optional[int] = None,
        dataset_record_id: Optional[int] = None,
        generation_params: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
    ) -> ModelExecution:
        """Persist a complete execution trace to the database."""
        req_id = request_id or str(uuid.uuid4())

        # Calculate cost only if pricing is explicitly configured
        cost_estimate: Optional[float] = None
        if (
            model_config.cost_per_1k_input_tokens is not None
            and model_config.cost_per_1k_output_tokens is not None
        ):
            cost_estimate = round(
                (input_tokens / 1000.0) * model_config.cost_per_1k_input_tokens
                + (output_tokens / 1000.0) * model_config.cost_per_1k_output_tokens,
                6,
            )

        execution = ModelExecution(
            request_id=req_id,
            experiment_id=experiment_id,
            experiment_run_id=experiment_run_id,
            model_config_id=model_config.id,
            prompt_version_id=prompt_version_id,
            dataset_record_id=dataset_record_id,
            input_prompt=input_prompt,
            output_text=output_text,
            status=status,
            error_category=error_category,
            error_details=error_details,
            start_time=start_time,
            end_time=end_time,
            latency_ms=round(latency_ms, 2),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            generation_parameters=json.dumps(generation_params or {}),
            cost_estimate=cost_estimate,
        )
        self.session.add(execution)
        await self.session.flush()

        # Add structured initial log
        log_msg = (
            f"Execution finished on '{model_config.display_name}'. "
            f"Status={status.value}, Latency={latency_ms:.1f}ms, Tokens={input_tokens + output_tokens}."
        )
        if error_details:
            log_msg += f" Error: {error_details}"

        log_entry = ExecutionLog(
            execution_id=execution.id,
            timestamp=end_time,
            level="INFO" if status == ExecutionStatus.SUCCESS else "ERROR",
            message=log_msg,
            metadata_json=json.dumps({
                "request_id": req_id,
                "error_category": error_category.value,
                "latency_ms": latency_ms,
            }),
        )
        self.session.add(log_entry)
        await self.session.commit()
        await self.session.refresh(execution)
        return execution

