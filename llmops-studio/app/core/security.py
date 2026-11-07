"""Security controls, timeouts, request validation, and safe error helpers."""
import html
import re
from typing import Any, Dict


def sanitize_input_text(text: str) -> str:
    """Sanitize user-provided text to prevent injection or invalid controls."""
    if not isinstance(text, str):
        return ""
    # Strip null bytes and control characters while preserving standard whitespace
    cleaned = "".join(ch for ch in text if ch == "\n" or ch == "\r" or ch == "\t" or ord(ch) >= 32)
    return cleaned.strip()


def validate_generation_params(params: Dict[str, Any]) -> Dict[str, Any]:
    """Validate and enforce bounds on LLM generation parameters."""
    validated: Dict[str, Any] = {}

    temp = params.get("temperature", 0.7)
    try:
        temp_val = float(temp)
        validated["temperature"] = max(0.0, min(2.0, temp_val))
    except (ValueError, TypeError):
        validated["temperature"] = 0.7

    max_tokens = params.get("max_tokens", 1024)
    try:
        max_tokens_val = int(max_tokens)
        validated["max_tokens"] = max(1, min(8192, max_tokens_val))
    except (ValueError, TypeError):
        validated["max_tokens"] = 1024

    top_p = params.get("top_p", 1.0)
    try:
        top_p_val = float(top_p)
        validated["top_p"] = max(0.0, min(1.0, top_p_val))
    except (ValueError, TypeError):
        validated["top_p"] = 1.0

    timeout = params.get("timeout_seconds", 30)
    try:
        timeout_val = int(timeout)
        validated["timeout_seconds"] = max(1, min(120, timeout_val))
    except (ValueError, TypeError):
        validated["timeout_seconds"] = 30

    return validated


def sanitize_error_message(error: Exception) -> str:
    """Return a safe, descriptive error message without leaking sensitive internal paths or keys."""
    raw = str(error)
    # Mask potential API keys or tokens
    masked = re.sub(r"(bearer\s+)[a-zA-Z0-9_\-\.]{10,}", r"\1[MASKED]", raw, flags=re.IGNORECASE)
    masked = re.sub(r"(api[_-]?key[:=]\s*)[a-zA-Z0-9_\-\.]{10,}", r"\1[MASKED]", masked, flags=re.IGNORECASE)
    return masked[:500]

