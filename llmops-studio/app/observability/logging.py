"""Observability structured log capture and retrieval."""
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import ExecutionLog


class ExecutionLogger:
    """Manages appending and retrieving execution trace logs."""

    @staticmethod
    async def log_event(
        session: AsyncSession,
        execution_id: int,
        level: str,
        message: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ExecutionLog:
        """Append an event to the execution audit trail."""
        log = ExecutionLog(
            execution_id=execution_id,
            timestamp=datetime.now(timezone.utc),
            level=level.upper(),
            message=message,
            metadata_json=json.dumps(metadata or {}),
        )
        session.add(log)
        await session.commit()
        await session.refresh(log)
        return log

    @staticmethod
    async def get_logs_for_execution(
        session: AsyncSession, execution_id: int
    ) -> List[ExecutionLog]:
        """Fetch all chronological logs for an execution."""
        stmt = (
            select(ExecutionLog)
            .where(ExecutionLog.execution_id == execution_id)
            .order_by(ExecutionLog.timestamp.asc())
        )
        res = await session.execute(stmt)
        return list(res.scalars().all())

