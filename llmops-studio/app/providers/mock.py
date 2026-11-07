"""Deterministic Mock Provider for offline testing and synthetic evaluations."""
import asyncio
import hashlib
import time
from typing import Any, Dict, List, Optional

from app.models.enums import ErrorCategory, ExecutionStatus
from app.providers.base import BaseModelProvider, ProviderResult
from app.schemas.provider import GenerationParameters


class MockProvider(BaseModelProvider):
    """Deterministic Mock LLM Provider for CI/CD and offline development."""

    def __init__(self, name: str = "MockProvider", base_url: Optional[str] = None):
        super().__init__(name=name, base_url=base_url)

    def _estimate_tokens(self, text: str) -> int:
        """Heuristic token count based on whitespace and punctuation."""
        if not text:
            return 0
        words = text.strip().split()
        return max(1, int(len(words) * 1.3) + len(text) // 25)

    async def generate(
        self,
        prompt: str,
        model: str,
        system_prompt: Optional[str] = None,
        params: Optional[GenerationParameters] = None,
    ) -> ProviderResult:
        """Generate deterministic response or simulate configured error conditions."""
        params = params or GenerationParameters()
        start = time.perf_counter()

        # Error simulation triggers for testing failure analysis
        if "[SIMULATE_TIMEOUT]" in prompt:
            await asyncio.sleep(0.05)
            elapsed = (time.perf_counter() - start) * 1000
            return ProviderResult(
                output_text="",
                latency_ms=elapsed,
                input_tokens=self._estimate_tokens(prompt),
                output_tokens=0,
                total_tokens=self._estimate_tokens(prompt),
                status=ExecutionStatus.TIMEOUT,
                error_category=ErrorCategory.TIMEOUT,
                error_details=f"Mock model execution timed out after {params.timeout_seconds}s.",
            )

        if "[SIMULATE_EMPTY]" in prompt:
            elapsed = (time.perf_counter() - start) * 1000
            return ProviderResult(
                output_text="",
                latency_ms=elapsed,
                input_tokens=self._estimate_tokens(prompt),
                output_tokens=0,
                total_tokens=self._estimate_tokens(prompt),
                status=ExecutionStatus.EMPTY_RESPONSE,
                error_category=ErrorCategory.EMPTY_RESPONSE,
                error_details="Model returned an empty completion string.",
            )

        if "[SIMULATE_ERROR]" in prompt:
            elapsed = (time.perf_counter() - start) * 1000
            return ProviderResult(
                output_text="",
                latency_ms=elapsed,
                input_tokens=self._estimate_tokens(prompt),
                output_tokens=0,
                total_tokens=self._estimate_tokens(prompt),
                status=ExecutionStatus.FAILED,
                error_category=ErrorCategory.PROVIDER_UNAVAILABLE,
                error_details="Simulated provider connection reset / 503 Service Unavailable.",
            )

        if "[SIMULATE_MALFORMED]" in prompt:
            elapsed = (time.perf_counter() - start) * 1000
            return ProviderResult(
                output_text="{ broken_json: [ unclosed string",
                latency_ms=elapsed,
                input_tokens=self._estimate_tokens(prompt),
                output_tokens=8,
                total_tokens=self._estimate_tokens(prompt) + 8,
                status=ExecutionStatus.FAILED,
                error_category=ErrorCategory.MALFORMED_OUTPUT,
                error_details="Output failed JSON schema parsing.",
            )

        # Deterministic generation
        # Short sleep to give non-zero realistic latency (5-15ms)
        await asyncio.sleep(0.01)

        input_tokens = self._estimate_tokens(prompt) + (self._estimate_tokens(system_prompt) if system_prompt else 0)

        # Build deterministic output text
        # If prompt contains "Context:", extract context to create grounded answers
        if "Context:" in prompt and "Question:" in prompt:
            parts = prompt.split("Context:", 1)[1].split("Question:", 1)
            context = parts[0].strip()
            question = parts[1].strip() if len(parts) > 1 else ""

            # Extract first sentence or snippet of context
            snippet = context.split(".")[0].strip() if "." in context else context[:100]
            output_text = f"Based on the provided context, {snippet}. This directly addresses your inquiry regarding {question[:50]}."
        elif "Python" in prompt:
            output_text = "In Python, you can achieve this using standard built-in libraries and asynchronous design patterns."
        elif "RAG" in prompt or "retrieval" in prompt.lower():
            output_text = "Retrieval-Augmented Generation (RAG) integrates an external knowledge base with a language model to synthesize grounded, up-to-date responses."
        else:
            # Deterministic hash summary
            prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:8]
            output_text = f"Deterministic response from model '{model}' [hash:{prompt_hash}]. Synthesized information based on input prompt."

        output_tokens = self._estimate_tokens(output_text)
        elapsed = (time.perf_counter() - start) * 1000

        return ProviderResult(
            output_text=output_text,
            latency_ms=round(elapsed, 2),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            status=ExecutionStatus.SUCCESS,
            error_category=ErrorCategory.NONE,
            raw_metadata={"model": model, "deterministic": True, "seed": 42},
        )

    async def check_health(self) -> Dict[str, Any]:
        """Health check for mock provider."""
        return {
            "status": "online",
            "is_available": True,
            "provider": self.name,
            "latency_ms": 1.2,
            "message": "Deterministic mock provider is operational.",
        }

    async def list_models(self) -> List[str]:
        """List simulated models."""
        return [
            "mock-deterministic",
            "mock-gpt4o-analogue",
            "mock-mistral-7b",
            "mock-llama3-8b",
        ]

