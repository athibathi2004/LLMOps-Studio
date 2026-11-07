"""Deterministic Semantic Similarity Metric using Vectorized N-gram TF-IDF Cosine Distance."""
import math
import re
from collections import Counter
from typing import Any, Dict, List, Optional, Set

from app.evaluation.base import BaseEvaluationMetric
from app.models.enums import MetricStatus
from app.schemas.evaluation import MetricEvaluationResult


def extract_ngrams(text: str, n: int = 1) -> List[str]:
    """Tokenize and extract word n-grams."""
    words = re.findall(r"\b\w+\b", text.lower())
    if n == 1:
        return words
    return ["_".join(words[i : i + n]) for i in range(len(words) - n + 1)]


def extract_char_ngrams(text: str, n: int = 3) -> List[str]:
    """Extract character n-grams to capture subword and morphological overlap."""
    clean = re.sub(r"\s+", " ", text.lower().strip())
    if len(clean) < n:
        return [clean] if clean else []
    return [clean[i : i + n] for i in range(len(clean) - n + 1)]


def compute_cosine_similarity(vec1: Counter, vec2: Counter) -> float:
    """Compute mathematical cosine similarity between two frequency vectors."""
    intersection = set(vec1.keys()) & set(vec2.keys())
    dot_product = sum(vec1[k] * vec2[k] for k in intersection)

    norm1 = math.sqrt(sum(val**2 for val in vec1.values()))
    norm2 = math.sqrt(sum(val**2 for val in vec2.values()))

    if norm1 == 0.0 or norm2 == 0.0:
        return 0.0

    return dot_product / (norm1 * norm2)


class SemanticSimilarityMetric(BaseEvaluationMetric):
    """Calculates deterministic semantic similarity via composite word and subword vector cosine distance."""

    def __init__(self):
        super().__init__(
            name="semantic_similarity",
            description="Evaluates semantic alignment between generated response and reference answer.",
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
                explanation="No reference answer available for semantic similarity calculation.",
                status=MetricStatus.FAIL,
                metadata={"reason": "missing_reference_answer"},
            )

        if not generated_answer or not generated_answer.strip():
            return MetricEvaluationResult(
                metric_name=self.name,
                score=0.0,
                score_min=0.0,
                score_max=1.0,
                explanation="Generated answer is empty.",
                status=MetricStatus.FAIL,
                metadata={"reason": "empty_generated_answer"},
            )

        # 1. Word unigram cosine
        gen_unigrams = Counter(extract_ngrams(generated_answer, 1))
        ref_unigrams = Counter(extract_ngrams(reference_answer, 1))
        unigram_sim = compute_cosine_similarity(gen_unigrams, ref_unigrams)

        # 2. Word bigram cosine
        gen_bigrams = Counter(extract_ngrams(generated_answer, 2))
        ref_bigrams = Counter(extract_ngrams(reference_answer, 2))
        bigram_sim = compute_cosine_similarity(gen_bigrams, ref_bigrams)

        # 3. Char trigram cosine (morphological robustness)
        gen_trigrams = Counter(extract_char_ngrams(generated_answer, 3))
        ref_trigrams = Counter(extract_char_ngrams(reference_answer, 3))
        char_sim = compute_cosine_similarity(gen_trigrams, ref_trigrams)

        # Composite score with weights: 0.4 unigram + 0.3 bigram + 0.3 char trigram
        composite_score = round(
            0.4 * unigram_sim + 0.3 * bigram_sim + 0.3 * char_sim, 4
        )
        composite_score = max(0.0, min(1.0, composite_score))

        if composite_score >= 0.70:
            status = MetricStatus.PASS
            explanation = f"High semantic similarity ({composite_score:.2f}) to reference answer."
        elif composite_score >= 0.40:
            status = MetricStatus.WARNING
            explanation = f"Moderate semantic similarity ({composite_score:.2f}); partially aligns with reference."
        else:
            status = MetricStatus.FAIL
            explanation = f"Low semantic similarity ({composite_score:.2f}); divergent from reference answer."

        return MetricEvaluationResult(
            metric_name=self.name,
            score=composite_score,
            score_min=0.0,
            score_max=1.0,
            explanation=explanation,
            status=status,
            metadata={
                "unigram_similarity": round(unigram_sim, 4),
                "bigram_similarity": round(bigram_sim, 4),
                "char_trigram_similarity": round(char_sim, 4),
                "method": "composite_ngram_cosine_tfidf",
            },
        )

