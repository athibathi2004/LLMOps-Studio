"""Prompt management and execution endpoints."""
import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.prompts.manager import PromptManager
from app.schemas.prompt import (
    PromptCreate,
    PromptDetailResponse,
    PromptExecuteRequest,
    PromptExecuteResponse,
    PromptResponse,
    PromptVersionCreate,
    PromptVersionResponse,
)

router = APIRouter()


@router.post("", response_model=PromptResponse, status_code=status.HTTP_201_CREATED, summary="Create a new prompt template")
async def create_prompt(
    payload: PromptCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new prompt template container and its first version."""
    prompt = await PromptManager.create_prompt(db, payload)
    latest_v = prompt.versions[0] if prompt.versions else None

    latest_response = None
    if latest_v:
        latest_response = PromptVersionResponse(
            id=latest_v.id,
            prompt_id=latest_v.prompt_id,
            version_number=latest_v.version_number,
            template_text=latest_v.template_text,
            input_variables=json.loads(latest_v.input_variables) if latest_v.input_variables else [],
            system_prompt=latest_v.system_prompt,
            description=latest_v.description,
            created_at=latest_v.created_at,
        )

    return PromptResponse(
        id=prompt.id,
        name=prompt.name,
        description=prompt.description,
        tags=prompt.tags,
        created_at=prompt.created_at,
        updated_at=prompt.updated_at,
        latest_version=latest_response,
        versions_count=len(prompt.versions),
    )


@router.get("", response_model=List[PromptResponse], summary="List all prompt templates")
async def list_prompts(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve all prompts with their latest version summary."""
    prompts = await PromptManager.list_prompts(db, limit=limit, offset=offset)
    output = []
    for p in prompts:
        latest_v = p.versions[0] if p.versions else None
        latest_resp = None
        if latest_v:
            latest_resp = PromptVersionResponse(
                id=latest_v.id,
                prompt_id=latest_v.prompt_id,
                version_number=latest_v.version_number,
                template_text=latest_v.template_text,
                input_variables=json.loads(latest_v.input_variables) if latest_v.input_variables else [],
                system_prompt=latest_v.system_prompt,
                description=latest_v.description,
                created_at=latest_v.created_at,
            )
        output.append(
            PromptResponse(
                id=p.id,
                name=p.name,
                description=p.description,
                tags=p.tags,
                created_at=p.created_at,
                updated_at=p.updated_at,
                latest_version=latest_resp,
                versions_count=len(p.versions),
            )
        )
    return output


@router.get("/{prompt_id}", response_model=PromptDetailResponse, summary="Get prompt details and all versions")
async def get_prompt(
    prompt_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Fetch prompt with complete version history."""
    prompt = await PromptManager.get_prompt_with_versions(db, prompt_id)
    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prompt with ID {prompt_id} not found.",
        )

    versions_resp = [
        PromptVersionResponse(
            id=v.id,
            prompt_id=v.prompt_id,
            version_number=v.version_number,
            template_text=v.template_text,
            input_variables=json.loads(v.input_variables) if v.input_variables else [],
            system_prompt=v.system_prompt,
            description=v.description,
            created_at=v.created_at,
        )
        for v in prompt.versions
    ]

    latest_resp = versions_resp[0] if versions_resp else None

    return PromptDetailResponse(
        id=prompt.id,
        name=prompt.name,
        description=prompt.description,
        tags=prompt.tags,
        created_at=prompt.created_at,
        updated_at=prompt.updated_at,
        latest_version=latest_resp,
        versions_count=len(versions_resp),
        versions=versions_resp,
    )


@router.post("/{prompt_id}/versions", response_model=PromptVersionResponse, status_code=status.HTTP_201_CREATED, summary="Create a new version for a prompt")
async def add_prompt_version(
    prompt_id: int,
    payload: PromptVersionCreate,
    db: AsyncSession = Depends(get_db),
):
    """Append a new version to an existing prompt template."""
    prompt = await PromptManager.get_prompt_with_versions(db, prompt_id)
    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prompt with ID {prompt_id} not found.",
        )

    version = await PromptManager.add_version(db, prompt_id, payload)
    return PromptVersionResponse(
        id=version.id,
        prompt_id=version.prompt_id,
        version_number=version.version_number,
        template_text=version.template_text,
        input_variables=json.loads(version.input_variables) if version.input_variables else [],
        system_prompt=version.system_prompt,
        description=version.description,
        created_at=version.created_at,
    )


@router.post("/{prompt_id}/execute", response_model=PromptExecuteResponse, summary="Execute a prompt template with live model")
async def execute_prompt(
    prompt_id: int,
    payload: PromptExecuteRequest,
    version_id: Optional[int] = Query(None, description="Optional specific version ID (defaults to latest)"),
    db: AsyncSession = Depends(get_db),
):
    """Interpolate variables into prompt template and invoke model execution with telemetry capture."""
    try:
        return await PromptManager.execute_prompt(
            session=db,
            prompt_id=prompt_id,
            version_id=version_id,
            model_id=payload.model_id,
            variables=payload.variables,
            params=payload.parameters,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

