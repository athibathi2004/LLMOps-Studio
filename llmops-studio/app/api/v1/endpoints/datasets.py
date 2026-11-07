"""Dataset management and import endpoints."""
import json
from typing import List, Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.datasets.manager import DatasetManager
from app.db.session import get_db
from app.schemas.dataset import (
    DatasetCreate,
    DatasetDetailResponse,
    DatasetRecordResponse,
    DatasetResponse,
)

router = APIRouter()


@router.post("", response_model=DatasetResponse, status_code=status.HTTP_201_CREATED, summary="Create a new dataset")
async def create_dataset(
    payload: DatasetCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new evaluation dataset container and persist its records."""
    try:
        dataset = await DatasetManager.create_dataset(db, payload)
        return DatasetResponse.model_validate(dataset)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get("", response_model=List[DatasetResponse], summary="List all datasets")
async def list_datasets(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve all evaluation datasets."""
    datasets = await DatasetManager.list_datasets(db, limit=limit, offset=offset)
    return [DatasetResponse.model_validate(d) for d in datasets]


@router.get("/{dataset_id}", response_model=DatasetDetailResponse, summary="Get dataset details and test cases")
async def get_dataset(
    dataset_id: int,
    include_records: bool = True,
    db: AsyncSession = Depends(get_db),
):
    """Fetch single dataset metadata and test cases."""
    dataset = await DatasetManager.get_dataset(db, dataset_id, include_records=include_records)
    if not dataset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dataset with ID {dataset_id} not found.",
        )

    records_resp = []
    if include_records and dataset.records:
        for r in dataset.records:
            ctx = json.loads(r.contexts) if r.contexts else []
            meta = json.loads(r.metadata_json) if r.metadata_json else {}
            records_resp.append(
                DatasetRecordResponse(
                    id=r.id,
                    dataset_id=r.dataset_id,
                    record_index=r.record_index,
                    question=r.question,
                    reference_answer=r.reference_answer,
                    contexts=ctx,
                    metadata=meta,
                    created_at=r.created_at,
                )
            )

    return DatasetDetailResponse(
        id=dataset.id,
        name=dataset.name,
        description=dataset.description,
        format=dataset.format,
        record_count=dataset.record_count,
        created_at=dataset.created_at,
        updated_at=dataset.updated_at,
        records=records_resp,
    )


@router.post("/upload", response_model=DatasetResponse, status_code=status.HTTP_201_CREATED, summary="Upload dataset from JSON or CSV file")
async def upload_dataset_file(
    name: str = Form(...),
    description: Optional[str] = Form(None),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Upload and validate a JSON or CSV dataset file."""
    content = await file.read()
    try:
        text_content = content.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File could not be decoded as UTF-8 text.",
        )

    filename = file.filename or ""
    is_csv = filename.lower().endswith(".csv") or file.content_type == "text/csv"

    try:
        if is_csv:
            dataset = await DatasetManager.import_csv(db, name, description, text_content)
        else:
            dataset = await DatasetManager.import_json(db, name, description, text_content)
        return DatasetResponse.model_validate(dataset)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

