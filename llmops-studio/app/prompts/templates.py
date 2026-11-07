"""Prompt Template parser and variable substitution engine."""
import re
from typing import Any, Dict, List, Set, Tuple


VARIABLE_REGEX = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}")


def extract_template_variables(template_text: str) -> List[str]:
    """Extract unique variable names defined in `{var_name}` format."""
    if not template_text:
        return []
    matches = VARIABLE_REGEX.findall(template_text)
    # Maintain original order while removing duplicates
    seen: Set[str] = set()
    ordered_vars: List[str] = []
    for var in matches:
        if var not in seen:
            seen.add(var)
            ordered_vars.append(var)
    return ordered_vars


def render_prompt_template(
    template_text: str, variables: Dict[str, Any]
) -> Tuple[str, List[str]]:
    """
    Safely render a prompt template with provided variables.

    Returns:
        Tuple of (rendered_prompt_string, list_of_missing_variables)
    """
    expected_vars = extract_template_variables(template_text)
    missing_vars = [var for var in expected_vars if var not in variables or variables[var] is None]

    rendered = template_text
    for var in expected_vars:
        placeholder = f"{{{var}}}"
        val = variables.get(var, f"[{var}: missing]")
        rendered = rendered.replace(placeholder, str(val))

    return rendered, missing_vars

