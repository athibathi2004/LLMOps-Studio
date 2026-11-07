"""System analytics and operational metrics endpoints."""
from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.service import analytics_service
from app.db.session import get_db
from app.schemas.analytics import (
    AnalyticsOverviewResponse,
    FailureAnalyticsResponse,
    ModelMetricSummary,
    PerformanceAnalyticsResponse,
)

router = APIRouter()


@router.get("/overview", response_model=AnalyticsOverviewResponse, summary="Get high-level platform KPI summary")
async def get_analytics_overview(db: AsyncSession = Depends(get_db)):
    """Retrieve system-wide totals: experiments, executions, average score, latency, and tokens."""
    return await analytics_service.get_overview(db)


@router.get("/models", response_model=List[ModelMetricSummary], summary="Get per-model benchmark rankings")
async def get_model_analytics(db: AsyncSession = Depends(get_db)):
    """Retrieve comparative metrics across all registered models."""
    return await analytics_service.get_model_metrics(db)


@router.get("/performance", response_model=PerformanceAnalyticsResponse, summary="Get latency and evaluation score distributions")
async def get_performance_analytics(db: AsyncSession = Depends(get_db)):
    """Retrieve latency timelines, score distribution histograms, and token volume."""
    return await analytics_service.get_performance_trends(db)


@router.get("/failures", response_model=FailureAnalyticsResponse, summary="Get failure analysis and root causes")
async def get_failure_analytics(db: AsyncSession = Depends(get_db)):
    """Retrieve categorized failure metrics, error breakdown, and recent trace diagnostics."""
    return await analytics_service.get_failure_analytics(db)

