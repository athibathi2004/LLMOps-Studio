"""Dataset service managing test cases and uploads."""
import json
from typing import Any, Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.datasets.validators import (
    parse_csv_dataset,
    parse_json_dataset,
    validate_dataset_records,
)
from app.models.models import Dataset, DatasetRecord
from app.schemas.dataset import DatasetCreate


class DatasetManager:
    """Manages datasets and test records."""

    @staticmethod
    async def create_dataset(
        session: AsyncSession, data: DatasetCreate
    ) -> Dataset:
        """Create a new dataset container and persist records."""
        dataset = Dataset(
            name=data.name,
            description=data.description,
            format=data.format,
            record_count=0,
        )
        session.add(dataset)
        await session.flush()

        if data.records:
            normalized = validate_dataset_records([r.model_dump() for r in data.records])
            for item in normalized:
                record = DatasetRecord(
                    dataset_id=dataset.id,
                    record_index=item["record_index"],
                    question=item["question"],
                    reference_answer=item["reference_answer"],
                    contexts=json.dumps(item["contexts"]),
                    metadata_json=json.dumps(item["metadata"]),
                )
                session.add(record)
            dataset.record_count = len(normalized)

        await session.commit()
        await session.refresh(dataset)
        return dataset

    @staticmethod
    async def import_json(
        session: AsyncSession, name: str, description: Optional[str], json_str: str
    ) -> Dataset:
        """Parse and import dataset from JSON string."""
        normalized = parse_json_dataset(json_str)
        dataset = Dataset(
            name=name,
            description=description,
            format="json",
            record_count=len(normalized),
        )
        session.add(dataset)
        await session.flush()

        for item in normalized:
            record = DatasetRecord(
                dataset_id=dataset.id,
                record_index=item["record_index"],
                question=item["question"],
                reference_answer=item["reference_answer"],
                contexts=json.dumps(item["contexts"]),
                metadata_json=json.dumps(item["metadata"]),
            )
            session.add(record)

        await session.commit()
        await session.refresh(dataset)
        return dataset

    @staticmethod
    async def import_csv(
        session: AsyncSession, name: str, description: Optional[str], csv_str: str
    ) -> Dataset:
        """Parse and import dataset from CSV text."""
        normalized = parse_csv_dataset(csv_str)
        dataset = Dataset(
            name=name,
            description=description,
            format="csv",
            record_count=len(normalized),
        )
        session.add(dataset)
        await session.flush()

        for item in normalized:
            record = DatasetRecord(
                dataset_id=dataset.id,
                record_index=item["record_index"],
                question=item["question"],
                reference_answer=item["reference_answer"],
                contexts=json.dumps(item["contexts"]),
                metadata_json=json.dumps(item["metadata"]),
            )
            session.add(record)

        await session.commit()
        await session.refresh(dataset)
        return dataset

    @staticmethod
    async def list_datasets(
        session: AsyncSession, limit: int = 50, offset: int = 0
    ) -> List[Dataset]:
        """List datasets ordered by recent updates."""
        stmt = (
            select(Dataset)
            .order_by(Dataset.updated_at.desc())
            .offset(offset)
            .limit(limit)
        )
        res = await session.execute(stmt)
        return list(res.scalars().all())

    @staticmethod
    async def get_dataset(
        session: AsyncSession, dataset_id: int, include_records: bool = False
    ) -> Optional[Dataset]:
        """Fetch dataset optionally with all test records."""
        if include_records:
            stmt = (
                select(Dataset)
                .where(Dataset.id == dataset_id)
                .options(selectinload(Dataset.records))
            )
        else:
            stmt = select(Dataset).where(Dataset.id == dataset_id)
        res = await session.execute(stmt)
        return res.scalar_one_or_none()

