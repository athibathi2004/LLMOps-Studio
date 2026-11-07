"""Response Completeness Evaluation Metric."""
from collections import Counter
from typing import Any, Dict, List, Optional

from app.evaluation.base import BaseEvaluationMetric
from app.evaluation.relevance import extract_keywords
from app.models.enums import MetricStatus
from app.schemas.evaluation import MetricEvaluationResult


class ResponseCompletenessMetric(BaseEvaluationMetric):
    """
    Evaluates whether the generated response thoroughly covers the information
    units, key entities, and expected facts specified in the reference answer.
    """

    def __init__(self):
        super().__init__(
            name="completeness",
            description="Evaluates whether the response contains all key elements from the reference answer.",
        )

    def evaluate(
        self,
        generated_answer: str,
        question: Optional[str] = None,
        reference_answer: Optional[str] = None,
        contexts: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> MetricEvaluationResult:
        if not reference_answer:
            return MetricEvaluationResult(
                metric_name=self.name,
                score=0.0,
                score_min=0.0,
                score_max=1.0,
                explanation="No reference answer available to assess completeness.",
                status=MetricStatus.FAIL,
                metadata={"reason": "missing_reference_answer"},
            )

        if not generated_answer or not generated_answer.strip():
            return MetricEvaluationResult(
                metric_name=self.name,
                score=0.0,
                score_min=0.0,
                score_max=1.0,
                explanation="Generated response is empty.",
                status=MetricStatus.FAIL,
                metadata={"reason": "empty_generated_answer"},
            )

        ref_keywords = extract_keywords(reference_answer)
        gen_keywords = set(extract_keywords(generated_answer))

        if not ref_keywords:
            ref_keywords = reference_answer.lower().split()

        ref_counter = Counter(ref_keywords)
        covered_units = sum(1 for kw in ref_counter if kw in gen_keywords)
        recall = covered_units / max(1, len(ref_counter))

        # Check relative length adequacy
        ref_words = max(1, len(reference_answer.split()))
        gen_words = len(generated_answer.split())
        ratio = min(1.0, gen_words / ref_words)

        score = round(max(0.0, min(1.0, 0.7 * recall + 0.3 * ratio)), 4)

        if score >= 0.75:
            status = MetricStatus.PASS
            explanation = f"Response is comprehensive (score: {score:.2f}); covers {covered_units}/{len(ref_counter)} key reference elements."
        elif score >= 0.45:
            status = MetricStatus.WARNING
            explanation = f"Response is partially complete (score: {score:.2f}); missing some key points."
        else:
            status = MetricStatus.FAIL
            explanation = f"Response is incomplete or sparse (score: {score:.2f}); major facts omitted."

        return MetricEvaluationResult(
            metric_name=self.name,
            score=score,
            score_min=0.0,
            score_max=1.0,
            explanation=explanation,
            status=status,
            metadata={
                "covered_key_terms": covered_units,
                "total_key_terms": len(ref_counter),
                "keyword_coverage_ratio": round(recall, 4),
                "length_ratio": round(ratio, 4),
            },
        )

