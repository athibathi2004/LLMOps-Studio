"""Tests for Model Comparison Benchmarking Engine."""
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.datasets.manager import DatasetManager
from app.experiments.comparison import model_comparison_engine
from app.experiments.manager import ExperimentManager
from app.experiments.runner import ExperimentRunner
from app.models.models import ModelConfiguration
from app.prompts.manager import PromptManager
from app.schemas.dataset import DatasetCreate, DatasetRecordCreate
from app.schemas.experiment import ExperimentCreate
from app.schemas.prompt import PromptCreate


@pytest.mark.asyncio
async def test_model_comparison_engine_output(db_session: AsyncSession):
    """Verify side-by-side model comparison metrics and pricing handling."""
    # Create dataset & prompt
    ds = await DatasetManager.create_dataset(
        db_session,
        DatasetCreate(
            name="Comparison Bench Dataset",
            records=[
                DatasetRecordCreate(
                    question="Explain Python Generators",
                    reference_answer="Generators yield values lazily.",
                    contexts=["Python generators use yield to produce values on demand."],
                )
            ],
        ),
    )

    prompt = await PromptManager.create_prompt(
        db_session,
        PromptCreate(
            name="Comparison Prompt",
            initial_template="Context: {context}\nQuestion: {question}",
        ),
    )

    stmt = select(ModelConfiguration).where(ModelConfiguration.model_identifier.like("mock%"))
    models = (await db_session.execute(stmt)).scalars().all()
    selected_ids = [m.id for m in models[:2]]

    exp = await ExperimentManager.create_experiment(
        db_session,
        ExperimentCreate(
            name="Comparison Test Run",
            dataset_id=ds.id,
            prompt_version_id=prompt.versions[0].id,
            selected_model_ids=selected_ids,
        ),
    )

    await ExperimentRunner.run_experiment(db_session, exp.id)

    # Compute comparison
    comparison = await model_comparison_engine.compare_experiment_models(db_session, exp.id)

    assert comparison.experiment_id == exp.id
    assert len(comparison.models) == len(selected_ids)
    for m in comparison.models:
        assert m.avg_latency_ms > 0
        assert m.avg_tokens > 0
        assert m.avg_evaluation_score >= 0.0
        # Cost validation: Never invent pricing
        if m.cost_available:
            assert m.cost_per_query is not None
        else:
            assert m.cost_per_query is None
            assert "unavailable" in m.cost_note.lower()

    assert len(comparison.side_by_side_samples) >= 1

