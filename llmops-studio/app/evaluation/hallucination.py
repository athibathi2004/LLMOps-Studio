"""Hallucination Risk Indicator heuristic evaluation."""
import re
from typing import Any, Dict, List, Optional, Set

from app.evaluation.base import BaseEvaluationMetric
from app.models.enums import MetricStatus
from app.schemas.evaluation import MetricEvaluationResult


COMMON_OPENERS: Set[str] = {
    "the", "this", "that", "these", "those", "based", "according", "therefore",
    "moreover", "furthermore", "however", "consequently", "in", "on", "at", "for",
    "with", "by", "from", "when", "what", "where", "how", "why", "who", "which",
    "because", "since", "as", "although", "while", "note", "first", "second",
    "finally", "overall", "specifically", "additionally", "such", "an", "a",
}


class HallucinationRiskMetric(BaseEvaluationMetric):
    """
    Heuristic Hallucination Risk Indicator.

    IMPORTANT ARCHITECTURAL NOTE:
    Heuristic entity extraction and lexical ungroundedness checks provide early risk signals,
    but are NOT a substitute for full human verification, formal semantic entailment models,
    or multi-agent consensus. Scores represent an indicator of hallucination risk.
    """

    def __init__(self):
        super().__init__(
            name="hallucination_risk",
            description="Detects ungrounded entities, fabricated numbers, or speculative assertions.",
        )

    def _extract_specific_entities(self, text: str) -> Set[str]:
        """Extract high-risk factual anchors: numbers, percentages, dates, and capitalized phrases."""
        entities = set()
        # Numbers, percentages, years, currency
        for match in re.findall(r"\b(?:\$|€|£)?\d+(?:\.\d+)?%?\b", text):
            entities.add(match.strip())
        # Capitalized multi-word named entities or acronyms
        for match in re.findall(r"\b[A-Z][a-zA-Z0-9_\-]{2,}\b", text):
            token = match.strip().lower()
            if token not in COMMON_OPENERS:
                entities.add(token)
        return entities

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
                explanation="No context available. Hallucination assessment requires grounding context.",
                status=MetricStatus.WARNING,
                metadata={"reason": "missing_contexts", "risk_level": "unknown"},
            )

        if not generated_answer or not generated_answer.strip():
            return MetricEvaluationResult(
                metric_name=self.name,
                score=0.0,
                score_min=0.0,
                score_max=1.0,
                explanation="Generated response is empty.",
                status=MetricStatus.PASS,
                metadata={"risk_level": "none"},
            )

        context_raw = " ".join(contexts)
        context_lower = context_raw.lower()
        context_entities = self._extract_specific_entities(context_raw)
        gen_entities = self._extract_specific_entities(generated_answer)

        # Flag entities present in generated answer but missing from context
        ungrounded_entities = [
            e for e in gen_entities
            if e not in context_entities and e not in context_lower
        ]

        total_entities = len(gen_entities)
        if total_entities == 0:
            risk_score = 0.05
        else:
            risk_score = len(ungrounded_entities) / total_entities

        # Contradiction cue words
        contradiction_cues = ["despite what is stated", "incorrectly claimed", "contrary to the context"]
        contradiction_detected = any(cue in generated_answer.lower() for cue in contradiction_cues)
        if contradiction_detected:
            risk_score = min(1.0, risk_score + 0.3)

        risk_score = round(max(0.0, min(1.0, risk_score)), 4)

        if risk_score <= 0.25:
            status = MetricStatus.PASS
            explanation = f"Low hallucination risk ({risk_score:.2f}). Most factual entities align with context."
        elif risk_score <= 0.55:
            status = MetricStatus.WARNING
            explanation = f"Moderate hallucination risk ({risk_score:.2f}). {len(ungrounded_entities)} ungrounded entity/number reference(s) detected."
        else:
            status = MetricStatus.FAIL
            explanation = f"High hallucination risk ({risk_score:.2f}). Significant proportion of unverified entities not found in context."

        return MetricEvaluationResult(
            metric_name=self.name,
            score=risk_score,
            score_min=0.0,
            score_max=1.0,
            explanation=explanation,
            status=status,
            metadata={
                "risk_level": "high" if risk_score > 0.55 else ("moderate" if risk_score > 0.25 else "low"),
                "total_entities_detected": total_entities,
                "ungrounded_entities_count": len(ungrounded_entities),
                "sample_ungrounded_entities": ungrounded_entities[:5],
                "contradiction_detected": contradiction_detected,
                "limitation_note": "Deterministic heuristic indicator. Does not guarantee absolute factual verification.",
            },
        )
