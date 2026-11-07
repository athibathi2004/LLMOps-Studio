"""Dedicated RAG Triad and Pipeline Evaluator."""
from typing import Any, Dict, List, Optional

from app.evaluation.faithfulness import FaithfulnessMetric
from app.evaluation.hallucination import HallucinationRiskMetric
from app.evaluation.relevance import AnswerRelevanceMetric, ContextRelevanceMetric
from app.schemas.evaluation import (
    MetricEvaluationResult,
    RAGEvaluationRequest,
    RAGEvaluationResponse,
    RAGTriadScores,
)


class RAGEvaluator:
    """
    RAG Evaluation Engine computing the canonical RAG Triad:
    1. Context Relevance: Are the retrieved passages pertinent to the question?
    2. Groundedness / Faithfulness: Is the answer derived strictly from the context?
    3. Answer Relevance: Does the generated answer satisfy the original user question?
    4. Context Coverage: How much of the necessary context information was synthesized?
    """

    def __init__(self):
        self.context_relevance_metric = ContextRelevanceMetric()
        self.faithfulness_metric = FaithfulnessMetric()
        self.answer_relevance_metric = AnswerRelevanceMetric()
        self.hallucination_metric = HallucinationRiskMetric()

    def evaluate_pipeline(self, request: RAGEvaluationRequest) -> RAGEvaluationResponse:
        """Execute full RAG Triad evaluation workflow."""
        # 1. Context Relevance
        res_ctx_rel = self.context_relevance_metric.evaluate(
            generated_answer=request.generated_answer,
            question=request.question,
            reference_answer=request.reference_answer,
            contexts=request.retrieved_contexts,
        )

        # 2. Faithfulness
        res_faith = self.faithfulness_metric.evaluate(
            generated_answer=request.generated_answer,
            question=request.question,
            reference_answer=request.reference_answer,
            contexts=request.retrieved_contexts,
        )

        # 3. Answer Relevance
        res_ans_rel = self.answer_relevance_metric.evaluate(
            generated_answer=request.generated_answer,
            question=request.question,
            reference_answer=request.reference_answer,
            contexts=request.retrieved_contexts,
        )

        # 4. Hallucination Risk
        res_hallucination = self.hallucination_metric.evaluate(
            generated_answer=request.generated_answer,
            question=request.question,
            reference_answer=request.reference_answer,
            contexts=request.retrieved_contexts,
        )

        # Context coverage estimation: ratio of retrieved context words referenced in answer
        total_ctx_words = sum(len(c.split()) for c in request.retrieved_contexts)
        ans_words = len(request.generated_answer.split())
        context_coverage = min(1.0, round(ans_words / max(20, total_ctx_words * 0.4), 4))

        # Overall composite RAG Score: harmonic mean or balanced weighted average of the Triad
        c_rel = res_ctx_rel.score
        faith = res_faith.score
        a_rel = res_ans_rel.score

        # Weighted: 35% faithfulness, 35% answer relevance, 30% context relevance
        overall_score = round(0.35 * faith + 0.35 * a_rel + 0.30 * c_rel, 4)

        triad_scores = RAGTriadScores(
            context_relevance=c_rel,
            faithfulness=faith,
            answer_relevance=a_rel,
            context_coverage=context_coverage,
            overall_rag_score=overall_score,
        )

        hallucination_detected = res_hallucination.score > 0.40

        explanation = (
            f"RAG Triad Score: {overall_score:.2f} (Context Relevance: {c_rel:.2f}, "
            f"Faithfulness: {faith:.2f}, Answer Relevance: {a_rel:.2f}). "
            f"{'Warning: Hallucination indicators detected.' if hallucination_detected else 'Response appears well-grounded in context.'}"
        )

        details: List[MetricEvaluationResult] = [
            res_ctx_rel,
            res_faith,
            res_ans_rel,
            res_hallucination,
        ]

        return RAGEvaluationResponse(
            triad_scores=triad_scores,
            hallucination_detected=hallucination_detected,
            hallucination_risk_score=res_hallucination.score,
            details=details,
            explanation=explanation,
        )


rag_evaluator = RAGEvaluator()

