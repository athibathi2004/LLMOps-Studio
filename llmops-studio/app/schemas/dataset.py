"""Pydantic schemas for Datasets and Dataset Records."""
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class DatasetRecordCreate(BaseModel):
    question: str = Field(..., min_length=1)
    reference_answer: Optional[str] = None
    contexts: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


class DatasetRecordResponse(BaseModel):
    id: int
    dataset_id: int
    record_index: int
    question: str
    reference_answer: Optional[str] = None
    contexts: List[str] = []
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DatasetCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=150)
    description: Optional[str] = None
    format: str = Field(default="json", pattern="^(json|csv)$")
    records: Optional[List[DatasetRecordCreate]] = None


class DatasetResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    format: str
    record_count: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DatasetDetailResponse(DatasetResponse):
    records: List[DatasetRecordResponse] = []

