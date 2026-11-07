"""Experiment management service for creating, querying, and updating experiments."""
import json
from typing import Any, Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.enums import ExperimentStatus
from app.models.models import (
    Dataset,
    Experiment,
    ExperimentRun,
    ModelConfiguration,
    PromptVersion,
)
from app.schemas.experiment import ExperimentCreate


class ExperimentManager:
    """Manages experiment records and their child runs."""

    @staticmethod
    async def create_experiment(
        session: AsyncSession, data: ExperimentCreate
    ) -> Experiment:
        """Create an experiment container and initialize sub-runs for each model."""
        # 1. Verify Dataset
        dataset = await session.get(Dataset, data.dataset_id)
        if not dataset:
            raise ValueError(f"Dataset with ID {data.dataset_id} does not exist.")

        # 2. Verify Prompt Version
        prompt_version = await session.get(PromptVersion, data.prompt_version_id)
        if not prompt_version:
            raise ValueError(f"PromptVersion with ID {data.prompt_version_id} does not exist.")

        # 3. Create Experiment
        experiment = Experiment(
            name=data.name,
            description=data.description,
            dataset_id=data.dataset_id,
            prompt_version_id=data.prompt_version_id,
            generation_parameters=json.dumps(
                data.generation_parameters.model_dump() if data.generation_parameters else {}
            ),
            status=ExperimentStatus.PENDING,
            total_runs=len(data.selected_model_ids),
            completed_runs=0,
            failed_runs=0,
        )
        session.add(experiment)
        await session.flush()

        # 4. Create an ExperimentRun for each model
        for idx, model_id in enumerate(data.selected_model_ids):
            model_cfg = await session.get(ModelConfiguration, model_id)
            if not model_cfg:
                raise ValueError(f"ModelConfiguration with ID {model_id} not found.")

            run = ExperimentRun(
                experiment_id=experiment.id,
                model_config_id=model_id,
                status=ExperimentStatus.PENDING,
                run_index=idx + 1,
            )
            session.add(run)

        await session.commit()
        await session.refresh(experiment)
        return experiment

    @staticmethod
    async def get_experiment(
        session: AsyncSession, experiment_id: int
    ) -> Optional[Experiment]:
        """Fetch experiment with its runs, dataset, and prompt."""
        stmt = (
            select(Experiment)
            .where(Experiment.id == experiment_id)
            .options(
                selectinload(Experiment.runs).selectinload(ExperimentRun.model_config),
                selectinload(Experiment.dataset),
                selectinload(Experiment.prompt_version),
            )
        )
        res = await session.execute(stmt)
        return res.scalar_one_or_none()

    @staticmethod
    async def list_experiments(
        session: AsyncSession, limit: int = 50, offset: int = 0
    ) -> List[Experiment]:
        """List experiments ordered by creation time descending."""
        stmt = (
            select(Experiment)
            .options(selectinload(Experiment.runs))
            .order_by(Experiment.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        res = await session.execute(stmt)
        return list(res.scalars().all())

