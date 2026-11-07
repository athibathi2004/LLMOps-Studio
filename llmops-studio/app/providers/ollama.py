"""Ollama Model Provider integration."""
import time
from typing import Any, Dict, List, Optional
import httpx

from app.models.enums import ErrorCategory, ExecutionStatus
from app.providers.base import BaseModelProvider, ProviderResult
from app.schemas.provider import GenerationParameters


class OllamaProvider(BaseModelProvider):
    """Adapter for interacting with local or remote Ollama daemon."""

    def __init__(self, name: str = "Ollama", base_url: str = "http://localhost:11434"):
        super().__init__(name=name, base_url=base_url.rstrip("/"))

    async def generate(
        self,
        prompt: str,
        model: str,
        system_prompt: Optional[str] = None,
        params: Optional[GenerationParameters] = None,
    ) -> ProviderResult:
        """Call Ollama /api/generate endpoint."""
        params = params or GenerationParameters()
        start = time.perf_counter()

        payload: Dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": params.temperature,
                "top_p": params.top_p,
                "num_predict": params.max_tokens,
            },
        }
        if system_prompt:
            payload["system"] = system_prompt

        timeout = httpx.Timeout(float(params.timeout_seconds), connect=5.0)

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(f"{self.base_url}/api/generate", json=payload)

                elapsed_ms = (time.perf_counter() - start) * 1000

                if response.status_code == 404:
                    return ProviderResult(
                        output_text="",
                        latency_ms=round(elapsed_ms, 2),
                        status=ExecutionStatus.FAILED,
                        error_category=ErrorCategory.CONFIGURATION_ERROR,
                        error_details=f"Ollama model '{model}' not found on server. Run 'ollama pull {model}'.",
                    )

                if response.status_code != 200:
                    return ProviderResult(
                        output_text="",
                        latency_ms=round(elapsed_ms, 2),
                        status=ExecutionStatus.FAILED,
                        error_category=ErrorCategory.PROVIDER_UNAVAILABLE,
                        error_details=f"Ollama returned HTTP {response.status_code}: {response.text[:200]}",
                    )

                data = response.json()
                output_text = data.get("response", "")

                if not output_text.strip():
                    return ProviderResult(
                        output_text="",
                        latency_ms=round(elapsed_ms, 2),
                        status=ExecutionStatus.EMPTY_RESPONSE,
                        error_category=ErrorCategory.EMPTY_RESPONSE,
                        error_details="Ollama returned an empty response string.",
                    )

                input_tokens = data.get("prompt_eval_count", len(prompt.split()) + 5)
                output_tokens = data.get("eval_count", len(output_text.split()))

                return ProviderResult(
                    output_text=output_text,
                    latency_ms=round(elapsed_ms, 2),
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    total_tokens=input_tokens + output_tokens,
                    status=ExecutionStatus.SUCCESS,
                    error_category=ErrorCategory.NONE,
                    raw_metadata={
                        "total_duration": data.get("total_duration"),
                        "load_duration": data.get("load_duration"),
                    },
                )

        except httpx.ConnectError:
            elapsed_ms = (time.perf_counter() - start) * 1000
            return ProviderResult(
                output_text="",
                latency_ms=round(elapsed_ms, 2),
                status=ExecutionStatus.FAILED,
                error_category=ErrorCategory.PROVIDER_UNAVAILABLE,
                error_details=f"Could not connect to Ollama daemon at {self.base_url}. Verify it is running.",
            )

        except (httpx.TimeoutException, httpx.ReadTimeout):
            elapsed_ms = (time.perf_counter() - start) * 1000
            return ProviderResult(
                output_text="",
                latency_ms=round(elapsed_ms, 2),
                status=ExecutionStatus.TIMEOUT,
                error_category=ErrorCategory.TIMEOUT,
                error_details=f"Ollama request timed out after {params.timeout_seconds} seconds.",
            )

        except Exception as exc:
            elapsed_ms = (time.perf_counter() - start) * 1000
            return ProviderResult(
                output_text="",
                latency_ms=round(elapsed_ms, 2),
                status=ExecutionStatus.FAILED,
                error_category=ErrorCategory.UNKNOWN,
                error_details=f"Unexpected error calling Ollama: {str(exc)}",
            )

    async def check_health(self) -> Dict[str, Any]:
        """Verify Ollama endpoint connectivity."""
        start = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                res = await client.get(f"{self.base_url}/api/tags")
                elapsed_ms = (time.perf_counter() - start) * 1000
                if res.status_code == 200:
                    models = [m.get("name") for m in res.json().get("models", [])]
                    return {
                        "status": "online",
                        "is_available": True,
                        "provider": self.name,
                        "latency_ms": round(elapsed_ms, 2),
                        "message": f"Connected to Ollama daemon with {len(models)} model(s) available.",
                        "models": models,
                    }
                return {
                    "status": "error",
                    "is_available": False,
                    "provider": self.name,
                    "latency_ms": round(elapsed_ms, 2),
                    "message": f"Ollama endpoint responded with HTTP {res.status_code}.",
                }
        except Exception as exc:
            return {
                "status": "offline",
                "is_available": False,
                "provider": self.name,
                "latency_ms": None,
                "message": f"Ollama daemon unreachable at {self.base_url}: {str(exc)}",
            }

    async def list_models(self) -> List[str]:
        """Fetch downloaded models list from Ollama."""
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                res = await client.get(f"{self.base_url}/api/tags")
                if res.status_code == 200:
                    return [m.get("name") for m in res.json().get("models", [])]
        except Exception:
            pass
        return ["llama3:latest", "mistral:latest"]

