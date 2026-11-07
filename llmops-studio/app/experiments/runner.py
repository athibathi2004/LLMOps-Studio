"""Experiment execution runner orchestrating model generation and evaluation."""
import json
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.evaluation.engine import evaluation_engine
from app.models.enums import ErrorCategory, ExecutionStatus, ExperimentStatus
from app.models.models import (
    Dataset,
    DatasetRecord,
    Experiment,
    ExperimentRun,
    ModelConfiguration,
    ModelExecution,
    PromptVersion,
)
from app.observability.tracker import ExecutionTracker
from app.prompts.templates import render_prompt_template
from app.providers.registry import provider_registry
from app.schemas.provider import GenerationParameters


class ExperimentRunner:
    """Orchestrates running an experiment across dataset items and models."""

    @staticmethod
    async def run_experiment(
        session: AsyncSession, experiment_id: int
    ) -> Experiment:
        """Execute all model runs within an experiment against its dataset."""
        # 1. Fetch Experiment with dependencies
        stmt = (
            select(Experiment)
            .where(Experiment.id == experiment_id)
            .options(
                selectinload(Experiment.runs).selectinload(ExperimentRun.model_config).selectinload(ModelConfiguration.provider),
                selectinload(Experiment.dataset).selectinload(Dataset.records),
                selectinload(Experiment.prompt_version),
            )
        )
        res = await session.execute(stmt)
        experiment = res.scalar_one_or_none()
        if not experiment:
            raise ValueError(f"Experiment with ID {experiment_id} not found.")

        # Update experiment status to RUNNING
        experiment.status = ExperimentStatus.RUNNING
        await session.commit()

        dataset = experiment.dataset
        prompt_version = experiment.prompt_version
        runs = experiment.runs
        records = dataset.records

        # Parse generation parameters
        gen_params_dict = {}
        if experiment.generation_parameters:
            try:
                gen_params_dict = json.loads(experiment.generation_parameters)
            except Exception:
                pass
        gen_params = GenerationParameters(**gen_params_dict) if gen_params_dict else GenerationParameters()

        tracker = ExecutionTracker(session)
        total_completed = 0
        total_failed = 0

        # Execute each model run
        for run in runs:
            model_cfg = run.model_config
            provider = provider_registry.get_adapter_by_type(model_cfg.provider.provider_type)
            if not provider:
                provider = provider_registry.get_adapter("mock")

            run.status = ExperimentStatus.RUNNING
            run.started_at = datetime.now(timezone.utc)
            await session.commit()

            run_start_time = time.perf_counter()
            run_failures = 0
            run_successes = 0

            for rec in records:
                # Prepare template variables from dataset record
                contexts_list = json.loads(rec.contexts) if rec.contexts else []
                variables = {
                    "question": rec.question,
                    "reference_answer": rec.reference_answer or "",
                    "context": "\n".join(contexts_list) if contexts_list else "",
                }
                # Also include custom metadata if present
                if rec.metadata_json:
                    try:
                        rec_meta = json.loads(rec.metadata_json)
                        if isinstance(rec_meta, dict):
                            variables.update(rec_meta)
                    except Exception:
                        pass

                rendered_prompt, missing = render_prompt_template(
                    prompt_version.template_text, variables
                )

                exec_start = datetime.now(timezone.utc)
                start_clock = time.perf_counter()

                try:
                    gen_result = await provider.generate(
                        prompt=rendered_prompt,
                        model=model_cfg.model_identifier,
                        system_prompt=prompt_version.system_prompt,
                        params=gen_params,
                    )
                except Exception as exc:
                    elapsed = (time.perf_counter() - start_clock) * 1000
                    cat = tracker.categorize_error(exc)
                    gen_result = None
                    execution = await tracker.record_execution(
                        model_config=model_cfg,
                        input_prompt=rendered_prompt,
                        output_text="",
                        status=ExecutionStatus.FAILED,
                        start_time=exec_start,
                        end_time=datetime.now(timezone.utc),
                        latency_ms=elapsed,
                        input_tokens=len(rendered_prompt.split()),
                        output_tokens=0,
                        error_category=cat,
                        error_details=str(exc),
                        experiment_id=experiment.id,
                        experiment_run_id=run.id,
                        prompt_version_id=prompt_version.id,
                        dataset_record_id=rec.id,
                        generation_params=gen_params_dict,
                    )
                    run_failures += 1
                    continue

                exec_end = datetime.now(timezone.utc)

                execution = await tracker.record_execution(
                    model_config=model_cfg,
                    input_prompt=rendered_prompt,
                    output_text=gen_result.output_text,
                    status=gen_result.status,
                    start_time=exec_start,
                    end_time=exec_end,
                    latency_ms=gen_result.latency_ms,
                    input_tokens=gen_result.input_tokens,
                    output_tokens=gen_result.output_tokens,
                    error_category=gen_result.error_category,
                    error_details=gen_result.error_details,
                    experiment_id=experiment.id,
                    experiment_run_id=run.id,
                    prompt_version_id=prompt_version.id,
                    dataset_record_id=rec.id,
                    generation_params=gen_params_dict,
                )

                if gen_result.status == ExecutionStatus.SUCCESS:
                    run_successes += 1
                    # Perform automated evaluation
                    eval_res = evaluation_engine.evaluate(
                        generated_answer=gen_result.output_text,
                        question=rec.question,
                        reference_answer=rec.reference_answer,
                        contexts=contexts_list,
                    )
                    await evaluation_engine.persist_evaluation(
                        session=session,
                        execution_id=execution.id,
                        evaluation_response=eval_res,
                        experiment_id=experiment.id,
                    )
                else:
                    run_failures += 1

            # Finalize run
            run_total_ms = (time.perf_counter() - run_start_time) * 1000
            run.completed_at = datetime.now(timezone.utc)
            run.latency_ms = round(run_total_ms, 2)

            if run_failures > 0 and run_successes == 0:
                run.status = ExperimentStatus.FAILED
                run.error_message = f"All {len(records)} test cases failed for model {model_cfg.display_name}."
                total_failed += 1
            else:
                run.status = ExperimentStatus.COMPLETED
                total_completed += 1

            await session.commit()

        # Update experiment aggregate status
        experiment.completed_runs = total_completed
        experiment.failed_runs = total_failed
        if total_completed > 0:
            experiment.status = ExperimentStatus.COMPLETED
        else:
            experiment.status = ExperimentStatus.FAILED

        await session.commit()
        await session.refresh(experiment)
        return experiment

