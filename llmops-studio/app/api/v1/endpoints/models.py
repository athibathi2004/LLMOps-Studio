"""Model registry and configuration endpoints."""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.models.models import ModelConfiguration, ModelProvider
from app.providers.registry import provider_registry
from app.schemas.provider import (
    ModelConfigCreate,
    ModelConfigResponse,
    ModelHealthCheckResponse,
)

router = APIRouter()


@router.get("", response_model=List[ModelConfigResponse], summary="List all registered models")
async def list_models(
    available_only: bool = False,
    db: AsyncSession = Depends(get_db),
):
    """Retrieve list of registered model configurations with provider metadata."""
    stmt = select(ModelConfiguration).options(selectinload(ModelConfiguration.provider))
    if available_only:
        stmt = stmt.where(ModelConfiguration.is_available.is_(True))
    stmt = stmt.order_by(ModelConfiguration.display_name.asc())

    res = await db.execute(stmt)
    models = res.scalars().all()

    output = []
    for m in models:
        item = ModelConfigResponse.model_validate(m)
        item.provider_name = m.provider.name if m.provider else "Unknown"
        output.append(item)
    return output


@router.post("/register", response_model=ModelConfigResponse, status_code=status.HTTP_201_CREATED, summary="Register a new model configuration")
async def register_model(
    payload: ModelConfigCreate,
    db: AsyncSession = Depends(get_db),
):
    """Register a new model with specific hyperparameters and pricing."""
    # Find provider
    provider = None
    if payload.provider_id:
        provider = await db.get(ModelProvider, payload.provider_id)
    elif payload.provider_name:
        stmt = select(ModelProvider).where(ModelProvider.name.ilike(f"%{payload.provider_name}%"))
        res = await db.execute(stmt)
        provider = res.scalars().first()

    if not provider:
        # Default to first active provider
        stmt = select(ModelProvider).where(ModelProvider.is_active.is_(True))
        provider = (await db.execute(stmt)).scalars().first()
        if not provider:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No active model provider found to associate with this model.",
            )

    # Check for duplicate model identifier under same provider
    dup_stmt = select(ModelConfiguration).where(
        ModelConfiguration.provider_id == provider.id,
        ModelConfiguration.model_identifier == payload.model_identifier,
    )
    existing = (await db.execute(dup_stmt)).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Model identifier '{payload.model_identifier}' already registered under provider '{provider.name}'.",
        )

    model_cfg = ModelConfiguration(
        provider_id=provider.id,
        model_identifier=payload.model_identifier,
        display_name=payload.display_name,
        description=payload.description,
        default_temperature=payload.default_temperature,
        default_max_tokens=payload.default_max_tokens,
        default_top_p=payload.default_top_p,
        timeout_seconds=payload.timeout_seconds,
        cost_per_1k_input_tokens=payload.cost_per_1k_input_tokens,
        cost_per_1k_output_tokens=payload.cost_per_1k_output_tokens,
        is_available=True,
    )
    db.add(model_cfg)
    await db.commit()
    await db.refresh(model_cfg)

    response = ModelConfigResponse.model_validate(model_cfg)
    response.provider_name = provider.name
    return response


@router.get("/{model_id}", response_model=ModelConfigResponse, summary="Get model configuration by ID")
async def get_model(
    model_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Fetch details of a single model configuration."""
    stmt = (
        select(ModelConfiguration)
        .where(ModelConfiguration.id == model_id)
        .options(selectinload(ModelConfiguration.provider))
    )
    model = (await db.execute(stmt)).scalar_one_or_none()
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ModelConfiguration with ID {model_id} not found.",
        )

    response = ModelConfigResponse.model_validate(model)
    response.provider_name = model.provider.name
    return response


@router.get("/{model_id}/health", response_model=ModelHealthCheckResponse, summary="Check model availability")
async def check_model_health(
    model_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Perform a live ping / readiness check on the model's provider endpoint."""
    stmt = (
        select(ModelConfiguration)
        .where(ModelConfiguration.id == model_id)
        .options(selectinload(ModelConfiguration.provider))
    )
    model = (await db.execute(stmt)).scalar_one_or_none()
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ModelConfiguration with ID {model_id} not found.",
        )

    provider = provider_registry.get_adapter_by_type(model.provider.provider_type)
    if not provider:
        provider = provider_registry.get_adapter("mock")

    health_info = await provider.check_health()
    is_avail = bool(health_info.get("is_available", False))

    return ModelHealthCheckResponse(
        model_id=model.id,
        model_identifier=model.model_identifier,
        provider=model.provider.name,
        is_available=is_avail,
        latency_ms=health_info.get("latency_ms"),
        message=health_info.get("message", "Model provider ping completed."),
    )

