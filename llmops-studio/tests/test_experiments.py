"""Tests for Experiment Manager and asynchronous Experiment Runner."""
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.datasets.manager import DatasetManager
from app.experiments.manager import ExperimentManager
from app.experiments.runner import ExperimentRunner
from app.models.enums import ExperimentStatus
from app.models.models import ModelConfiguration, ModelExecution
from app.prompts.manager import PromptManager
from app.schemas.dataset import DatasetCreate, DatasetRecordCreate
from app.schemas.experiment import ExperimentCreate
from app.schemas.prompt import PromptCreate


@pytest.mark.asyncio
async def test_full_experiment_lifecycle(db_session: AsyncSession):
    """Verify defining an experiment with dataset and running it across models."""
    # 1. Create Dataset
    ds = await DatasetManager.create_dataset(
        db_session,
        DatasetCreate(
            name="Experiment Test Dataset",
            records=[
                DatasetRecordCreate(
                    question="What is 10 + 20?",
                    reference_answer="30",
                    contexts=["Basic math states that 10 plus 20 equals 30."],
                ),
                DatasetRecordCreate(
                    question="What is 5 * 6?",
                    reference_answer="30",
                    contexts=["5 multiplied by 6 is 30."],
                ),
            ],
        ),
    )

    # 2. Create Prompt
    prompt = await PromptManager.create_prompt(
        db_session,
        PromptCreate(
            name="Math Prompt",
            initial_template="Context: {context}\nQuestion: {question}",
        ),
    )

    # 3. Get Models
    stmt = select(ModelConfiguration).where(ModelConfiguration.model_identifier.like("mock%"))
    models = (await db_session.execute(stmt)).scalars().all()
    assert len(models) >= 1
    selected_ids = [m.id for m in models[:2]]

    # 4. Create Experiment
    exp_payload = ExperimentCreate(
        name="Unit Test Experiment",
        dataset_id=ds.id,
        prompt_version_id=prompt.versions[0].id,
        selected_model_ids=selected_ids,
    )
    experiment = await ExperimentManager.create_experiment(db_session, exp_payload)
    assert experiment.status == ExperimentStatus.PENDING
    assert experiment.total_runs == len(selected_ids)

    # 5. Execute Experiment
    completed_exp = await ExperimentRunner.run_experiment(db_session, experiment.id)
    assert completed_exp.status == ExperimentStatus.COMPLETED
    assert completed_exp.completed_runs == len(selected_ids)

    # 6. Verify Executions persisted
    exec_stmt = select(ModelExecution).where(ModelExecution.experiment_id == experiment.id)
    execs = (await db_session.execute(exec_stmt)).scalars().all()
    # 2 test cases * len(selected_ids) models
    assert len(execs) == 2 * len(selected_ids)

