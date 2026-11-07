"""Answer Relevance and Context Relevance evaluation metrics."""
import math
import re
from collections import Counter
from typing import Any, Dict, List, Optional, Set

from app.evaluation.base import BaseEvaluationMetric
from app.evaluation.semantic_similarity import compute_cosine_similarity, extract_ngrams
from app.models.enums import MetricStatus
from app.schemas.evaluation import MetricEvaluationResult

STOP_WORDS: Set[str] = {
    "a", "an", "the", "in", "on", "at", "by", "for", "with", "about", "against",
    "between", "into", "through", "during", "before", "after", "above", "below",
    "to", "from", "up", "down", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "and", "but", "or", "because", "as",
    "until", "while", "of", "it", "its", "this", "that", "these", "those", "can",
    "could", "will", "would", "shall", "should", "what", "which", "who", "whom",
    "how", "why", "where", "when",
}


def extract_keywords(text: str) -> List[str]:
    """Extract significant non-stopword tokens."""
    tokens = re.findall(r"\b[a-zA-Z0-9_\-]{2,}\b", text.lower())
    return [t for t in tokens if t not in STOP_WORDS]


class AnswerRelevanceMetric(BaseEvaluationMetric):
    """Measures how directly the generated answer addresses the user query."""

    def __init__(self):
        super().__init__(
            name="answer_relevance",
            description="Evaluates whether the generated response directly addresses the question.",
        )

    def evaluate(
        self,
        generated_answer: str,
        question: Optional[str] = None,
        reference_answer: Optional[str] = None,
        contexts: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> MetricEvaluationResult:
        if not question or not question.strip():
            return MetricEvaluationResult(
                metric_name=self.name,
                score=0.0,
                score_min=0.0,
                score_max=1.0,
                explanation="No question supplied to evaluate answer relevance.",
                status=MetricStatus.FAIL,
                metadata={"reason": "missing_question"},
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

        q_keywords = extract_keywords(question)
        ans_keywords = extract_keywords(generated_answer)

        if not q_keywords:
            q_keywords = [w.lower() for w in question.split()]

        # Keyword recall from question in the answer
        q_counter = Counter(q_keywords)
        ans_counter = Counter(ans_keywords)

        matched_keywords = sum(1 for k in q_counter if k in ans_counter)
        keyword_recall = matched_keywords / max(1, len(q_counter))

        # Vector cosine between question and answer
        vec_sim = compute_cosine_similarity(q_counter, ans_counter)

        # Length sanity check: penalize degenerate outputs (< 5 words or > 2000 words without substance)
        words_count = len(generated_answer.split())
        length_penalty = 1.0
        if words_count < 4:
            length_penalty = 0.5
        elif words_count < 8:
            length_penalty = 0.8

        raw_score = (0.6 * keyword_recall + 0.4 * vec_sim) * length_penalty
        score = round(max(0.0, min(1.0, raw_score)), 4)

        if score >= 0.65:
            status = MetricStatus.PASS
            explanation = f"Answer is highly relevant to question (score: {score:.2f})."
        elif score >= 0.35:
            status = MetricStatus.WARNING
            explanation = f"Answer is moderately relevant (score: {score:.2f}); partial keyword coverage."
        else:
            status = MetricStatus.FAIL
            explanation = f"Answer appears irrelevant or off-topic (score: {score:.2f})."

        return MetricEvaluationResult(
            metric_name=self.name,
            score=score,
            score_min=0.0,
            score_max=1.0,
            explanation=explanation,
            status=status,
            metadata={
                "matched_question_keywords": matched_keywords,
                "total_question_keywords": len(q_counter),
                "keyword_recall": round(keyword_recall, 4),
                "cosine_alignment": round(vec_sim, 4),
                "answer_words": words_count,
            },
        )


class ContextRelevanceMetric(BaseEvaluationMetric):
    """Evaluates whether retrieved passages are pertinent to the user question."""

    def __init__(self):
        super().__init__(
            name="context_relevance",
            description="Evaluates whether retrieved context passages are relevant to the user query.",
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
                explanation="No contexts supplied to evaluate context relevance.",
                status=MetricStatus.FAIL,
                metadata={"reason": "missing_contexts"},
            )

        if not question:
            return MetricEvaluationResult(
                metric_name=self.name,
                score=0.0,
                score_min=0.0,
                score_max=1.0,
                explanation="No question supplied for context relevance assessment.",
                status=MetricStatus.FAIL,
                metadata={"reason": "missing_question"},
            )

        q_keywords = set(extract_keywords(question))
        if not q_keywords:
            q_keywords = set(question.lower().split())

        relevant_chunks = 0
        total_chunks = len(contexts)
        chunk_scores: List[float] = []

        for ctx in contexts:
            ctx_tokens = set(extract_keywords(ctx))
            overlap = len(q_keywords & ctx_tokens)
            coverage = overlap / max(1, len(q_keywords))
            chunk_scores.append(coverage)
            if coverage >= 0.25:  # At least 25% question keywords present
                relevant_chunks += 1

        avg_coverage = sum(chunk_scores) / max(1, total_chunks)
        chunk_ratio = relevant_chunks / max(1, total_chunks)

        score = round(max(0.0, min(1.0, 0.5 * avg_coverage + 0.5 * chunk_ratio)), 4)

        if score >= 0.60:
            status = MetricStatus.PASS
            explanation = f"Retrieved contexts are pertinent to the query ({relevant_chunks}/{total_chunks} chunks)."
        elif score >= 0.30:
            status = MetricStatus.WARNING
            explanation = f"Moderate context relevance ({relevant_chunks}/{total_chunks} chunks pertinent)."
        else:
            status = MetricStatus.FAIL
            explanation = f"Low context relevance ({relevant_chunks}/{total_chunks} chunks pertinent); high noise."

        return MetricEvaluationResult(
            metric_name=self.name,
            score=score,
            score_min=0.0,
            score_max=1.0,
            explanation=explanation,
            status=status,
            metadata={
                "total_chunks": total_chunks,
                "relevant_chunks": relevant_chunks,
                "chunk_scores": [round(s, 3) for s in chunk_scores],
            },
        )

