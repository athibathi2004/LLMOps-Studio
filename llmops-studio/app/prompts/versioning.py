"""Prompt versioning and diffing utilities."""
import difflib
import json
from typing import Any, Dict, List
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Prompt, PromptVersion
from app.prompts.templates import extract_template_variables


async def create_new_prompt_version(
    session: AsyncSession,
    prompt_id: int,
    template_text: str,
    system_prompt: str | None = None,
    description: str | None = None,
) -> PromptVersion:
    """Create and append an incremented version to an existing prompt."""
    # Find highest existing version
    stmt = select(func.max(PromptVersion.version_number)).where(PromptVersion.prompt_id == prompt_id)
    max_ver = (await session.execute(stmt)).scalar_one_or_none() or 0
    next_ver = max_ver + 1

    extracted_vars = extract_template_variables(template_text)

    version = PromptVersion(
        prompt_id=prompt_id,
        version_number=next_ver,
        template_text=template_text,
        input_variables=json.dumps(extracted_vars),
        system_prompt=system_prompt,
        description=description,
    )
    session.add(version)
    await session.commit()
    await session.refresh(version)
    return version


def compare_prompt_versions(
    v1: PromptVersion, v2: PromptVersion
) -> Dict[str, Any]:
    """Compute line diff, variable changes, and metadata contrast between two versions."""
    lines_v1 = v1.template_text.splitlines(keepends=True)
    lines_v2 = v2.template_text.splitlines(keepends=True)

    diff = list(
        difflib.unified_diff(
            lines_v1,
            lines_v2,
            fromfile=f"v{v1.version_number}",
            tofile=f"v{v2.version_number}",
        )
    )

    vars_v1 = set(json.loads(v1.input_variables) if v1.input_variables else [])
    vars_v2 = set(json.loads(v2.input_variables) if v2.input_variables else [])

    added_vars = sorted(list(vars_v2 - vars_v1))
    removed_vars = sorted(list(vars_v1 - vars_v2))

    return {
        "version_a": v1.version_number,
        "version_b": v2.version_number,
        "diff_text": "".join(diff),
        "added_variables": added_vars,
        "removed_variables": removed_vars,
        "system_prompt_changed": v1.system_prompt != v2.system_prompt,
    }

