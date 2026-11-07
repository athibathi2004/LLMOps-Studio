"""Provider Registry managing LLM provider lifecycle and adapters."""
from typing import Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.enums import ProviderType
from app.models.models import ModelConfiguration, ModelProvider
from app.providers.base import BaseModelProvider
from app.providers.mock import MockProvider
from app.providers.ollama import OllamaProvider


class ProviderRegistry:
    """Central registry for instantiating and accessing model providers."""

    def __init__(self):
        self._providers: Dict[str, BaseModelProvider] = {}
        # Pre-register built-in adapters
        self.register_adapter("Mock", MockProvider(name="Mock"))
        self.register_adapter(
            "Ollama", OllamaProvider(name="Ollama", base_url=settings.OLLAMA_BASE_URL)
        )

    def register_adapter(self, name: str, provider: BaseModelProvider) -> None:
        """Register a provider instance by name."""
        self._providers[name.lower()] = provider

    def get_adapter(self, name: str) -> Optional[BaseModelProvider]:
        """Retrieve a provider adapter by name."""
        return self._providers.get(name.lower())

    def get_adapter_by_type(self, provider_type: ProviderType) -> Optional[BaseModelProvider]:
        """Retrieve a provider adapter by provider type enum."""
        if provider_type == ProviderType.MOCK:
            return self._providers.get("mock")
        if provider_type == ProviderType.OLLAMA:
            return self._providers.get("ollama")
        return self._providers.get("mock")

    async def seed_defaults(self, session: AsyncSession) -> None:
        """Seed default providers and model configurations if not present."""
        # 1. Seed Mock Provider
        mock_provider_stmt = select(ModelProvider).where(ModelProvider.name == "Mock Provider")
        res = await session.execute(mock_provider_stmt)
        mock_provider = res.scalar_one_or_none()
        if not mock_provider:
            mock_provider = ModelProvider(
                name="Mock Provider",
                provider_type=ProviderType.MOCK,
                base_url=None,
                is_active=True,
            )
            session.add(mock_provider)
            await session.flush()

        # 2. Seed Ollama Provider
        ollama_provider_stmt = select(ModelProvider).where(ModelProvider.name == "Ollama Local")
        res = await session.execute(ollama_provider_stmt)
        ollama_provider = res.scalar_one_or_none()
        if not ollama_provider:
            ollama_provider = ModelProvider(
                name="Ollama Local",
                provider_type=ProviderType.OLLAMA,
                base_url=settings.OLLAMA_BASE_URL,
                is_active=True,
            )
            session.add(ollama_provider)
            await session.flush()

        # 3. Seed Default Model Configurations
        default_models = [
            {
                "provider_id": mock_provider.id,
                "model_identifier": "mock-deterministic",
                "display_name": "Deterministic Mock Engine",
                "description": "Standard deterministic mock model for offline benchmarking and unit tests.",
                "default_temperature": 0.0,
                "default_max_tokens": 1024,
                "default_top_p": 1.0,
                "timeout_seconds": 30,
                "cost_per_1k_input_tokens": 0.0,
                "cost_per_1k_output_tokens": 0.0,
                "is_available": True,
            },
            {
                "provider_id": mock_provider.id,
                "model_identifier": "mock-gpt4o-analogue",
                "display_name": "Mock GPT-4o Analogue",
                "description": "Simulated frontier model with high faithfulness and completeness characteristics.",
                "default_temperature": 0.5,
                "default_max_tokens": 2048,
                "default_top_p": 0.95,
                "timeout_seconds": 45,
                "cost_per_1k_input_tokens": 0.005,
                "cost_per_1k_output_tokens": 0.015,
                "is_available": True,
            },
            {
                "provider_id": ollama_provider.id,
                "model_identifier": "llama3:latest",
                "display_name": "Meta Llama 3 (Ollama)",
                "description": "Local Meta Llama 3 8B model hosted via Ollama daemon.",
                "default_temperature": 0.7,
                "default_max_tokens": 1024,
                "default_top_p": 0.9,
                "timeout_seconds": 60,
                "cost_per_1k_input_tokens": None,  # Cost unavailable for local open-source
                "cost_per_1k_output_tokens": None,
                "is_available": True,
            },
            {
                "provider_id": ollama_provider.id,
                "model_identifier": "mistral:latest",
                "display_name": "Mistral 7B (Ollama)",
                "description": "Local Mistral 7B Instruct model hosted via Ollama daemon.",
                "default_temperature": 0.7,
                "default_max_tokens": 1024,
                "default_top_p": 0.9,
                "timeout_seconds": 60,
                "cost_per_1k_input_tokens": None,
                "cost_per_1k_output_tokens": None,
                "is_available": True,
            },
        ]

        for m_data in default_models:
            check_stmt = select(ModelConfiguration).where(
                ModelConfiguration.model_identifier == m_data["model_identifier"]
            )
            existing = (await session.execute(check_stmt)).scalar_one_or_none()
            if not existing:
                model_cfg = ModelConfiguration(**m_data)
                session.add(model_cfg)

        await session.commit()


provider_registry = ProviderRegistry()

