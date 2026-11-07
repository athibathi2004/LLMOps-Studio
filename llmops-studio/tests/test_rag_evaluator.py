"""Tests for dedicated RAG Triad evaluator."""
from app.evaluation.rag_evaluator import rag_evaluator
from app.schemas.evaluation import RAGEvaluationRequest


def test_rag_triad_evaluation_high_quality():
    """Verify high-quality RAG response scores strongly across the RAG Triad."""
    request = RAGEvaluationRequest(
        question="What is the computational complexity of Scaled Dot-Product Attention?",
        retrieved_contexts=[
            "Scaled Dot-Product Attention computes softmax(QK^T / sqrt(d)) V.",
            "Because Q and K are length N, matrix multiplication requires N x N operations.",
            "Therefore, standard attention has a quadratic complexity of O(N^2) in sequence length N.",
        ],
        generated_answer="Based on the context, Scaled Dot-Product Attention requires O(N^2) quadratic complexity in sequence length N.",
        reference_answer="Scaled Dot-Product Attention has a quadratic O(N^2) computational complexity.",
    )

    result = rag_evaluator.evaluate_pipeline(request)

    assert result.triad_scores.context_relevance >= 0.50
    assert result.triad_scores.faithfulness >= 0.80
    assert result.triad_scores.answer_relevance >= 0.60
    assert result.triad_scores.overall_rag_score >= 0.65
    assert result.hallucination_detected is False
    assert len(result.details) == 4


def test_rag_triad_evaluation_hallucination_detection():
    """Verify hallucination detection triggers when response contradicts or departs from context."""
    request = RAGEvaluationRequest(
        question="What is the capital of Australia?",
        retrieved_contexts=[
            "Canberra is the federal capital of Australia, established following a compromise between Sydney and Melbourne."
        ],
        generated_answer="The capital of Australia is Brisbane with a population of 85 million residents in the year 1700.",
    )

    result = rag_evaluator.evaluate_pipeline(request)

    assert result.triad_scores.faithfulness < 0.50
    assert result.hallucination_detected is True
    assert result.hallucination_risk_score > 0.40

