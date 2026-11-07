"""Health check endpoint."""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_db
from app.schemas.common import HealthStatus

router = APIRouter()


@router.get("/health", response_model=HealthStatus, summary="Check platform health and database connectivity")
async def check_health(db: AsyncSession = Depends(get_db)):
    """Return platform operational status and database responsiveness."""
    db_status = "connected"
    try:
        await db.execute(text("SELECT 1"))
    except Exception as exc:
        db_status = f"unreachable: {str(exc)}"

    return HealthStatus(
        status="healthy" if db_status == "connected" else "degraded",
        service=settings.APP_NAME,
        version=settings.APP_VERSION,
        database=db_status,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )

