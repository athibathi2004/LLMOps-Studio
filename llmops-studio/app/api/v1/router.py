"""Main API v1 router consolidating all domain endpoints."""
from fastapi import APIRouter

from app.api.v1.endpoints import (
    analytics,
    datasets,
    evaluations,
    executions,
    experiments,
    health,
    models,
    prompts,
)

api_router = APIRouter()

api_router.include_router(health.router, tags=["Health"])
api_router.include_router(models.router, prefix="/models", tags=["Models"])
api_router.include_router(prompts.router, prefix="/prompts", tags=["Prompts"])
api_router.include_router(datasets.router, prefix="/datasets", tags=["Datasets"])
api_router.include_router(experiments.router, prefix="/experiments", tags=["Experiments"])
api_router.include_router(evaluations.router, prefix="/evaluations", tags=["Evaluations"])
api_router.include_router(executions.router, prefix="/executions", tags=["Executions & Observability"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["Analytics & Insights"])

