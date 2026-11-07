"""Tests for Model Provider abstraction, Mock Provider, and Ollama integration."""
import pytest
from app.models.enums import ErrorCategory, ExecutionStatus
from app.providers.base import BaseModelProvider
from app.providers.mock import MockProvider
from app.providers.ollama import OllamaProvider
from app.providers.registry import ProviderRegistry
from app.schemas.provider import GenerationParameters


@pytest.mark.asyncio
async def test_mock_provider_deterministic_generation():
    """Verify mock provider generates deterministic completions with non-zero tokens and latency."""
    provider = MockProvider()
    prompt = "Context: Python is an interpreted language. Question: What is Python?"
    res = await provider.generate(
        prompt=prompt,
        model="mock-deterministic",
        params=GenerationParameters(temperature=0.0, max_tokens=100),
    )

    assert res.status == ExecutionStatus.SUCCESS
    assert res.error_category == ErrorCategory.NONE
    assert "Python is an interpreted language" in res.output_text
    assert res.latency_ms > 0
    assert res.input_tokens > 0
    assert res.output_tokens > 0
    assert res.total_tokens == res.input_tokens + res.output_tokens


@pytest.mark.asyncio
async def test_mock_provider_timeout_simulation():
    """Verify mock provider handles simulated timeout trigger."""
    provider = MockProvider()
    res = await provider.generate(
        prompt="Execute task [SIMULATE_TIMEOUT]",
        model="mock-deterministic",
    )
    assert res.status == ExecutionStatus.TIMEOUT
    assert res.error_category == ErrorCategory.TIMEOUT
    assert "timed out" in res.error_details.lower()


@pytest.mark.asyncio
async def test_mock_provider_empty_response_simulation():
    """Verify mock provider handles simulated empty completion trigger."""
    provider = MockProvider()
    res = await provider.generate(
        prompt="Execute task [SIMULATE_EMPTY]",
        model="mock-deterministic",
    )
    assert res.status == ExecutionStatus.EMPTY_RESPONSE
    assert res.error_category == ErrorCategory.EMPTY_RESPONSE
    assert res.output_text == ""


@pytest.mark.asyncio
async def test_mock_provider_malformed_output_simulation():
    """Verify mock provider handles simulated malformed structured output trigger."""
    provider = MockProvider()
    res = await provider.generate(
        prompt="Execute task [SIMULATE_MALFORMED]",
        model="mock-deterministic",
    )
    assert res.status == ExecutionStatus.FAILED
    assert res.error_category == ErrorCategory.MALFORMED_OUTPUT


@pytest.mark.asyncio
async def test_mock_provider_health_check():
    """Verify mock provider health check returns available."""
    provider = MockProvider()
    health = await provider.check_health()
    assert health["is_available"] is True
    assert health["status"] == "online"


@pytest.mark.asyncio
async def test_ollama_provider_unreachable_connection():
    """Verify Ollama provider gracefully handles unreachable daemon connection."""
    # Point to nonexistent port
    provider = OllamaProvider(base_url="http://127.0.0.1:59999")
    res = await provider.generate(
        prompt="Hello world",
        model="llama3:latest",
    )
    assert res.status == ExecutionStatus.FAILED
    assert res.error_category == ErrorCategory.PROVIDER_UNAVAILABLE
    assert "could not connect" in res.error_details.lower()


@pytest.mark.asyncio
async def test_provider_registry_lifecycle():
    """Verify registering and retrieving providers through the central registry."""
    registry = ProviderRegistry()
    mock_p = registry.get_adapter("mock")
    assert mock_p is not None
    assert isinstance(mock_p, MockProvider)

    ollama_p = registry.get_adapter("ollama")
    assert ollama_p is not None
    assert isinstance(ollama_p, OllamaProvider)

