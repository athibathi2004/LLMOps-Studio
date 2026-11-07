"""Tests for Dataset ingestion, validation, and parsing."""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.datasets.manager import DatasetManager
from app.datasets.validators import (
    parse_csv_dataset,
    parse_json_dataset,
    validate_dataset_records,
)
from app.schemas.dataset import DatasetCreate, DatasetRecordCreate


def test_validate_empty_dataset_raises():
    """Verify validating an empty dataset raises ValueError."""
    with pytest.raises(ValueError, match="cannot be empty"):
        validate_dataset_records([])


def test_validate_missing_question_raises():
    """Verify test cases missing question field raise ValueError."""
    with pytest.raises(ValueError, match="missing required 'question'"):
        validate_dataset_records([{"reference_answer": "42"}])


def test_parse_json_dataset_valid():
    """Verify parsing valid JSON text with array structure."""
    raw_json = """
    [
        {
            "question": "What is 2+2?",
            "reference_answer": "4",
            "contexts": ["Basic arithmetic defines 2+2=4."]
        }
    ]
    """
    records = parse_json_dataset(raw_json)
    assert len(records) == 1
    assert records[0]["question"] == "What is 2+2?"
    assert records[0]["reference_answer"] == "4"
    assert len(records[0]["contexts"]) == 1


def test_parse_csv_dataset_valid():
    """Verify parsing CSV text with delimited contexts."""
    csv_text = 'question,reference_answer,contexts\n"Capital of France?","Paris","Paris is the capital of France.|||It is located on the Seine."'
    records = parse_csv_dataset(csv_text)
    assert len(records) == 1
    assert records[0]["question"] == "Capital of France?"
    assert records[0]["reference_answer"] == "Paris"
    assert len(records[0]["contexts"]) == 2


@pytest.mark.asyncio
async def test_dataset_manager_create(db_session: AsyncSession):
    """Verify DatasetManager persists dataset and individual test record rows."""
    create_payload = DatasetCreate(
        name="Test Ingestion Dataset",
        description="Dataset unit test",
        format="json",
        records=[
            DatasetRecordCreate(
                question="What is FastAPI?",
                reference_answer="An async Python framework.",
                contexts=["FastAPI is built on Starlette and Pydantic."],
            ),
            DatasetRecordCreate(
                question="What is Uvicorn?",
                reference_answer="An ASGI web server.",
            ),
        ],
    )

    dataset = await DatasetManager.create_dataset(db_session, create_payload)
    assert dataset.id is not None
    assert dataset.record_count == 2

    loaded = await DatasetManager.get_dataset(db_session, dataset.id, include_records=True)
    assert loaded is not None
    assert len(loaded.records) == 2
    assert loaded.records[0].question == "What is FastAPI?"

