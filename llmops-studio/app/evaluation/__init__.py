"""Evaluation engine and metrics collection."""
from app.evaluation.base import BaseEvaluationMetric
from app.evaluation.completeness import ResponseCompletenessMetric
from app.evaluation.engine import EvaluationEngine, evaluation_engine
from app.evaluation.exact_match import ExactMatchMetric
from app.evaluation.faithfulness import FaithfulnessMetric
from app.evaluation.hallucination import HallucinationRiskMetric
from app.evaluation.rag_evaluator import RAGEvaluator, rag_evaluator
from app.evaluation.relevance import AnswerRelevanceMetric, ContextRelevanceMetric
from app.evaluation.semantic_similarity import SemanticSimilarityMetric

__all__ = [
    "BaseEvaluationMetric",
    "ExactMatchMetric",
    "SemanticSimilarityMetric",
    "AnswerRelevanceMetric",
    "ContextRelevanceMetric",
    "FaithfulnessMetric",
    "ResponseCompletenessMetric",
    "HallucinationRiskMetric",
    "RAGEvaluator",
    "rag_evaluator",
    "EvaluationEngine",
    "evaluation_engine",
]

