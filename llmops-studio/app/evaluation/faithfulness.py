"""Faithfulness and Groundedness Evaluation Metric."""
import re
from typing import Any, Dict, List, Optional, Set

from app.evaluation.base import BaseEvaluationMetric
from app.evaluation.relevance import STOP_WORDS, extract_keywords
from app.models.enums import MetricStatus
from app.schemas.evaluation import MetricEvaluationResult


def split_into_sentences(text: str) -> List[str]:
    """Split text into individual declarative sentences/statements."""
    if not text:
        return []
    # Split on period, exclamation, or question mark followed by whitespace or newline
    sentences = re.split(r"(?<=[.!?])\s+|\n+", text)
    return [s.strip() for s in sentences if len(s.strip()) > 5]


class FaithfulnessMetric(BaseEvaluationMetric):
    """
    Evaluates factual consistency of the generated answer against supplied context passages.
    Measures the ratio of generated claims that can be inferred directly from the context.
    """

    def __init__(self):
        super().__init__(
            name="faithfulness",
            description="Evaluates whether claims in the generated response are grounded in the provided context.",
        )

    def evaluate(
        self,
        generated_answer: str,
        question: Optional[str] = None,
        reference_answer: Optional[str] = None,
        contexts: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> MetricEvaluationResult:
        if not contexts:
            return MetricEvaluationResult(
                metric_name=self.name,
                score=0.0,
                score_min=0.0,
                score_max=1.0,
                explanation="No context passages provided to verify faithfulness.",
                status=MetricStatus.FAIL,
                metadata={"reason": "missing_contexts"},
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

        # Combine all context chunks into a single searchable corpus
        corpus = " ".join(contexts).lower()
        corpus_keywords = set(extract_keywords(corpus))

        statements = split_into_sentences(generated_answer)
        if not statements:
            statements = [generated_answer]

        grounded_count = 0
        ungrounded_claims: List[str] = []

        for stmt in statements:
            stmt_keywords = extract_keywords(stmt)
            if not stmt_keywords:
                # Trivial statement without distinct content words
                grounded_count += 1
                continue

            # Check overlap of statement content tokens with context corpus
            overlap = [w for w in stmt_keywords if w in corpus_keywords]
            overlap_ratio = len(overlap) / len(stmt_keywords)

            # A statement is deemed grounded if >= 65% of its core content words exist in the context
            if overlap_ratio >= 0.65:
                grounded_count += 1
            else:
                ungrounded_claims.append(stmt[:120])

        score = round(grounded_count / max(1, len(statements)), 4)

        if score >= 0.80:
            status = MetricStatus.PASS
            explanation = f"High faithfulness ({score:.2f}): {grounded_count}/{len(statements)} statements grounded in context."
        elif score >= 0.50:
            status = MetricStatus.WARNING
            explanation = f"Moderate faithfulness ({score:.2f}): {len(ungrounded_claims)} ungrounded statement(s) detected."
        else:
            status = MetricStatus.FAIL
            explanation = f"Low faithfulness ({score:.2f}): generated response contains significant unsupported claims."

        return MetricEvaluationResult(
            metric_name=self.name,
            score=score,
            score_min=0.0,
            score_max=1.0,
            explanation=explanation,
            status=status,
            metadata={
                "total_statements": len(statements),
                "grounded_statements": grounded_count,
                "ungrounded_statements": len(ungrounded_claims),
                "flagged_claims": ungrounded_claims[:5],
            },
        )

