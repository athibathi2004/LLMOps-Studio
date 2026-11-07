"""Exact Match Evaluation Metric."""
import re
import string
from typing import Any, Dict, List, Optional

from app.evaluation.base import BaseEvaluationMetric
from app.models.enums import MetricStatus
from app.schemas.evaluation import MetricEvaluationResult


def normalize_text(text: str) -> str:
    """Normalize text by lowercasing, removing punctuation and trimming whitespace."""
    if not text:
        return ""
    # Lowercase
    normalized = text.lower()
    # Remove punctuation
    normalized = "".join(ch for ch in normalized if ch not in string.punctuation)
    # Collapse multiple whitespaces
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


class ExactMatchMetric(BaseEvaluationMetric):
    """Calculates strict and normalized Exact Match between generated and reference answers."""

    def __init__(self):
        super().__init__(
            name="exact_match",
            description="Measures whether the generated text exactly matches the reference answer.",
        )

    def evaluate(
        self,
        generated_answer: str,
        question: Optional[str] = None,
        reference_answer: Optional[str] = None,
        contexts: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> MetricEvaluationResult:
        if reference_answer is None:
            return MetricEvaluationResult(
                metric_name=self.name,
                score=0.0,
                score_min=0.0,
                score_max=1.0,
                explanation="No reference answer provided for exact match evaluation.",
                status=MetricStatus.FAIL,
                metadata={"reason": "missing_reference_answer"},
            )

        norm_gen = normalize_text(generated_answer)
        norm_ref = normalize_text(reference_answer)

        is_strict_match = generated_answer.strip() == reference_answer.strip()
        is_normalized_match = norm_gen == norm_ref

        if is_strict_match:
            score = 1.0
            status = MetricStatus.PASS
            explanation = "Strict character-for-character exact match with reference answer."
        elif is_normalized_match:
            score = 0.95
            status = MetricStatus.PASS
            explanation = "Normalized exact match (matched after whitespace/punctuation normalization)."
        else:
            score = 0.0
            status = MetricStatus.FAIL
            explanation = "Generated output does not match the reference answer."

        return MetricEvaluationResult(
            metric_name=self.name,
            score=score,
            score_min=0.0,
            score_max=1.0,
            explanation=explanation,
            status=status,
            metadata={
                "strict_match": is_strict_match,
                "normalized_match": is_normalized_match,
                "reference_length": len(reference_answer),
                "generated_length": len(generated_answer),
            },
        )

