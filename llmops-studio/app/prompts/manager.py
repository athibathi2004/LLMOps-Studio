"""Prompt Manager service handling templates, version history, and interactive execution."""
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.enums import ErrorCategory, ExecutionStatus
from app.models.models import (
    ExecutionLog,
    ModelConfiguration,
    ModelExecution,
    Prompt,
    PromptVersion,
)
from app.prompts.templates import extract_template_variables, render_prompt_template
from app.prompts.versioning import create_new_prompt_version
from app.providers.registry import provider_registry
from app.schemas.prompt import (
    PromptCreate,
    PromptExecuteResponse,
    PromptVersionCreate,
)
from app.schemas.provider import GenerationParameters


class PromptManager:
    """Service for managing prompts, versioning, and test runs."""

    @staticmethod
    async def create_prompt(
        session: AsyncSession, data: PromptCreate
    ) -> Prompt:
        """Create a new prompt container and initial version 1."""
        prompt = Prompt(
            name=data.name,
            description=data.description,
            tags=data.tags,
        )
        session.add(prompt)
        await session.flush()

        # Create Version 1
        vars_list = extract_template_variables(data.initial_template)
        v1 = PromptVersion(
            prompt_id=prompt.id,
            version_number=1,
            template_text=data.initial_template,
            input_variables=json.dumps(vars_list),
            system_prompt=data.system_prompt,
            description="Initial version",
        )
        session.add(v1)
        await session.commit()
        return await PromptManager.get_prompt_with_versions(session, prompt.id)

    @staticmethod
    async def get_prompt_with_versions(
        session: AsyncSession, prompt_id: int
    ) -> Optional[Prompt]:
        """Fetch prompt with all associated versions."""
        stmt = (
            select(Prompt)
            .where(Prompt.id == prompt_id)
            .options(selectinload(Prompt.versions))
        )
        res = await session.execute(stmt)
        return res.scalar_one_or_none()

    @staticmethod
    async def list_prompts(
        session: AsyncSession, limit: int = 50, offset: int = 0
    ) -> List[Prompt]:
        """List prompts with version relationship."""
        stmt = (
            select(Prompt)
            .options(selectinload(Prompt.versions))
            .order_by(Prompt.updated_at.desc())
            .offset(offset)
            .limit(limit)
        )
        res = await session.execute(stmt)
        return list(res.scalars().all())

    @staticmethod
    async def add_version(
        session: AsyncSession, prompt_id: int, data: PromptVersionCreate
    ) -> PromptVersion:
        """Append a new version to an existing prompt."""
        version = await create_new_prompt_version(
            session=session,
            prompt_id=prompt_id,
            template_text=data.template_text,
            system_prompt=data.system_prompt,
            description=data.description,
        )
        return version

    @staticmethod
    async def execute_prompt(
        session: AsyncSession,
        prompt_id: int,
        version_id: Optional[int],
        model_id: int,
        variables: Dict[str, Any],
        params: Optional[GenerationParameters] = None,
    ) -> PromptExecuteResponse:
        """Render a prompt version with variables and execute it on the designated model."""
        # 1. Fetch Model Configuration
        stmt_model = (
            select(ModelConfiguration)
            .where(ModelConfiguration.id == model_id)
            .options(selectinload(ModelConfiguration.provider))
        )
        model_cfg = (await session.execute(stmt_model)).scalar_one_or_none()
        if not model_cfg:
            raise ValueError(f"ModelConfiguration with id {model_id} not found.")

        # 2. Fetch Prompt Version
        if version_id:
            stmt_v = select(PromptVersion).where(PromptVersion.id == version_id)
        else:
            stmt_v = (
                select(PromptVersion)
                .where(PromptVersion.prompt_id == prompt_id)
                .order_by(PromptVersion.version_number.desc())
            )
        prompt_version = (await session.execute(stmt_v)).scalars().first()
        if not prompt_version:
            raise ValueError(f"Prompt version not found for prompt_id={prompt_id}.")

        # 3. Render Template
        rendered_prompt, missing = render_prompt_template(
            prompt_version.template_text, variables
        )

        # 4. Invoke Provider
        provider = provider_registry.get_adapter_by_type(model_cfg.provider.provider_type)
        if not provider:
            provider = provider_registry.get_adapter("mock")

        start_time = datetime.now(timezone.utc)
        result = await provider.generate(
            prompt=rendered_prompt,
            model=model_cfg.model_identifier,
            system_prompt=prompt_version.system_prompt,
            params=params,
        )
        end_time = datetime.now(timezone.utc)

        # 5. Compute Cost if pricing is configured
        cost_estimate: Optional[float] = None
        if (
            model_cfg.cost_per_1k_input_tokens is not None
            and model_cfg.cost_per_1k_output_tokens is not None
        ):
            cost_estimate = (
                (result.input_tokens / 1000.0) * model_cfg.cost_per_1k_input_tokens
                + (result.output_tokens / 1000.0) * model_cfg.cost_per_1k_output_tokens
            )

        # 6. Record Execution Trace
        req_id = str(uuid.uuid4())
        execution = ModelExecution(
            request_id=req_id,
            experiment_id=None,
            experiment_run_id=None,
            model_config_id=model_cfg.id,
            prompt_version_id=prompt_version.id,
            dataset_record_id=None,
            input_prompt=rendered_prompt,
            output_text=result.output_text,
            status=result.status,
            error_category=result.error_category,
            error_details=result.error_details,
            start_time=start_time,
            end_time=end_time,
            latency_ms=result.latency_ms,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            total_tokens=result.total_tokens,
            generation_parameters=json.dumps(params.model_dump() if params else {}),
            cost_estimate=cost_estimate,
        )
        session.add(execution)
        await session.flush()

        # Add structured execution log
        log_entry = ExecutionLog(
            execution_id=execution.id,
            timestamp=end_time,
            level="INFO" if result.status == ExecutionStatus.SUCCESS else "ERROR",
            message=f"Prompt executed on {model_cfg.display_name}. Status: {result.status}. Latency: {result.latency_ms}ms.",
            metadata_json=json.dumps({
                "request_id": req_id,
                "missing_vars": missing,
                "input_tokens": result.input_tokens,
                "output_tokens": result.output_tokens,
            }),
        )
        session.add(log_entry)
        await session.commit()

        return PromptExecuteResponse(
            execution_id=execution.id,
            request_id=req_id,
            model_name=model_cfg.display_name,
            rendered_prompt=rendered_prompt,
            output_text=result.output_text,
            latency_ms=result.latency_ms,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            total_tokens=result.total_tokens,
            status=result.status.value,
        )
