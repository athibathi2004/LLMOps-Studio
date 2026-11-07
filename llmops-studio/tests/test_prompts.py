"""Tests for Prompt template parsing, versioning, diffing, and execution."""
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import ModelConfiguration
from app.prompts.manager import PromptManager
from app.prompts.templates import extract_template_variables, render_prompt_template
from app.prompts.versioning import compare_prompt_versions
from app.schemas.prompt import PromptCreate, PromptVersionCreate


def test_template_variable_extraction():
    """Verify regex variable extraction identifies distinct variable names."""
    template = "Context: {context}\nQuestion: {question}\nTarget format: {format_type}. Again {context}."
    variables = extract_template_variables(template)
    assert variables == ["context", "question", "format_type"]


def test_template_variable_rendering():
    """Verify variable interpolation and missing variable detection."""
    template = "Answer {question} based on {context}."
    rendered, missing = render_prompt_template(
        template,
        {"question": "What is Python?", "context": "Python is dynamic."},
    )
    assert rendered == "Answer What is Python? based on Python is dynamic.."
    assert missing == []

    # Test with missing variable
    rendered_missing, missing_vars = render_prompt_template(
        template,
        {"question": "What is Python?"},
    )
    assert "context" in missing_vars
    assert "[context: missing]" in rendered_missing


@pytest.mark.asyncio
async def test_prompt_creation_and_versioning(db_session: AsyncSession):
    """Verify prompt creation generates initial version and supports incrementing versions."""
    create_payload = PromptCreate(
        name="Test QA Prompt",
        description="A prompt for unit testing",
        tags="test,unit",
        initial_template="Question: {question}",
    )
    prompt = await PromptManager.create_prompt(db_session, create_payload)
    assert prompt.id is not None
    assert len(prompt.versions) == 1
    assert prompt.versions[0].version_number == 1

    # Add second version
    v2 = await PromptManager.add_version(
        db_session,
        prompt.id,
        PromptVersionCreate(
            template_text="Context: {context}\nQuestion: {question}\nAnswer:",
            description="Added context slot",
        ),
    )
    assert v2.version_number == 2

    # Compare versions
    diff = compare_prompt_versions(prompt.versions[0], v2)
    assert diff["version_a"] == 1
    assert diff["version_b"] == 2
    assert "context" in diff["added_variables"]


@pytest.mark.asyncio
async def test_prompt_execution_flow(db_session: AsyncSession):
    """Verify executing a prompt renders template and captures an execution record."""
    prompt = await PromptManager.create_prompt(
        db_session,
        PromptCreate(
            name="Executable Prompt",
            initial_template="Explain {topic} in Python.",
        ),
    )

    # Fetch mock model
    stmt = select(ModelConfiguration).where(ModelConfiguration.model_identifier == "mock-deterministic")
    model_cfg = (await db_session.execute(stmt)).scalars().first()
    assert model_cfg is not None

    res = await PromptManager.execute_prompt(
        session=db_session,
        prompt_id=prompt.id,
        version_id=None,
        model_id=model_cfg.id,
        variables={"topic": "AsyncIO"},
    )

    assert res.execution_id > 0
    assert "Explain AsyncIO in Python" in res.rendered_prompt
    assert res.output_text != ""
    assert res.status == "SUCCESS"
    assert res.latency_ms > 0
