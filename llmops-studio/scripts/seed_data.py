"""Seed script to populate initial sample datasets, prompts, and run an initial experiment."""
import asyncio
import json
from pathlib import Path
import sys

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

from app.datasets.manager import DatasetManager
from app.db.session import async_session_factory, init_db
from app.experiments.manager import ExperimentManager
from app.experiments.runner import ExperimentRunner
from app.models.models import Dataset, Experiment, ModelConfiguration, Prompt, PromptVersion
from app.prompts.manager import PromptManager
from app.providers.registry import provider_registry
from app.schemas.dataset import DatasetCreate, DatasetRecordCreate
from app.schemas.experiment import ExperimentCreate
from app.schemas.prompt import PromptCreate


async def seed():
    print("[*] Initializing database...")
    await init_db()

    async with async_session_factory() as session:
        print("[*] Seeding default model providers and configurations...")
        await provider_registry.seed_defaults(session)

        # 1. Seed Datasets
        sample_data_dir = root_dir / "sample-data"

        rag_json_path = sample_data_dir / "rag_benchmarks.json"
        if rag_json_path.exists():
            with open(rag_json_path, "r", encoding="utf-8") as f:
                records = json.load(f)
            ds_create = DatasetCreate(
                name="Core CS & AI RAG Benchmark",
                description="Comprehensive evaluation test cases covering databases, distributed systems, and LLM attention.",
                format="json",
                records=[
                    DatasetRecordCreate(
                        question=r["question"],
                        reference_answer=r["reference_answer"],
                        contexts=r["contexts"],
                        metadata=r.get("metadata", {}),
                    )
                    for r in records
                ],
            )
            dataset = await DatasetManager.create_dataset(session, ds_create)
            print(f"[+] Created Dataset: '{dataset.name}' (ID: {dataset.id}, Records: {dataset.record_count})")

        # 2. Seed Prompts
        prompts_json_path = sample_data_dir / "prompt_templates.json"
        prompt_version = None
        if prompts_json_path.exists():
            with open(prompts_json_path, "r", encoding="utf-8") as f:
                prompts_data = json.load(f)
            for p_info in prompts_data:
                p_create = PromptCreate(
                    name=p_info["name"],
                    description=p_info["description"],
                    tags=p_info.get("tags"),
                    initial_template=p_info["template"],
                    system_prompt=p_info.get("system_prompt"),
                )
                prompt_obj = await PromptManager.create_prompt(session, p_create)
                print(f"[+] Created Prompt: '{prompt_obj.name}' (ID: {prompt_obj.id})")
                if not prompt_version and prompt_obj.versions:
                    prompt_version = prompt_obj.versions[0]

        # 3. Create and execute an initial benchmark experiment
        from sqlalchemy import select
        models = (await session.execute(select(ModelConfiguration))).scalars().all()
        selected_model_ids = [m.id for m in models if "mock" in m.model_identifier]

        if dataset and prompt_version and selected_model_ids:
            exp_create = ExperimentCreate(
                name="Baseline Multi-Model RAG Quality Evaluation",
                description="Comparative evaluation of mock deterministic engine vs GPT-4o analogue on core CS benchmark.",
                dataset_id=dataset.id,
                prompt_version_id=prompt_version.id,
                selected_model_ids=selected_model_ids,
            )
            experiment = await ExperimentManager.create_experiment(session, exp_create)
            print(f"[+] Created Experiment: '{experiment.name}' (ID: {experiment.id})")

            print("[*] Executing initial benchmark experiment across selected models...")
            completed_exp = await ExperimentRunner.run_experiment(session, experiment.id)
            print(f"[+] Experiment completed with status: {completed_exp.status.value}")

    print("[SUCCESS] All sample data and initial baseline experiment successfully seeded!")


if __name__ == "__main__":
    asyncio.run(seed())

