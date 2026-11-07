"""Base class for all evaluation metrics in LLMOps Studio."""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from app.models.enums import MetricStatus
from app.schemas.evaluation import MetricEvaluationResult


class BaseEvaluationMetric(ABC):
    """Abstract contract for metric calculation."""

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description

    @abstractmethod
    def evaluate(
        self,
        generated_answer: str,
        question: Optional[str] = None,
        reference_answer: Optional[str] = None,
        contexts: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> MetricEvaluationResult:
        """
        Evaluate generated model response against reference/context.

        Returns:
            MetricEvaluationResult containing score, range, explanation, status.
        """
        pass

