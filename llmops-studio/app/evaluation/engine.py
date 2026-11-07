"""Central Evaluation Engine coordinating all metric evaluations."""
from typing import Any, Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.evaluation.base import BaseEvaluationMetric
from app.evaluation.completeness import ResponseCompletenessMetric
from app.evaluation.exact_match import ExactMatchMetric
from app.evaluation.faithfulness import FaithfulnessMetric
from app.evaluation.hallucination import HallucinationRiskMetric
from app.evaluation.relevance import AnswerRelevanceMetric, ContextRelevanceMetric
from app.evaluation.semantic_similarity import SemanticSimilarityMetric
from app.models.enums import MetricStatus
from app.models.models import EvaluationMetric, EvaluationResult
from app.schemas.evaluation import EvaluationResultResponse, MetricEvaluationResult


class EvaluationEngine:
    """Orchestrates metric execution, score aggregation, and database persistence."""

    def __init__(self):
        self._metrics: Dict[str, BaseEvaluationMetric] = {
            "exact_match": ExactMatchMetric(),
            "semantic_similarity": SemanticSimilarityMetric(),
            "answer_relevance": AnswerRelevanceMetric(),
            "context_relevance": ContextRelevanceMetric(),
            "faithfulness": FaithfulnessMetric(),
            "completeness": ResponseCompletenessMetric(),
            "hallucination_risk": HallucinationRiskMetric(),
        }

    def get_registered_metric_names(self) -> List[str]:
        """Return list of supported evaluation metric keys."""
        return list(self._metrics.keys())

    def evaluate(
        self,
        generated_answer: str,
        question: Optional[str] = None,
        reference_answer: Optional[str] = None,
        contexts: Optional[List[str]] = None,
        selected_metrics: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> EvaluationResultResponse:
        """Run selected evaluation metrics and compute weighted composite verdict."""
        metrics_to_run = selected_metrics or [
            "exact_match",
            "semantic_similarity",
            "answer_relevance",
            "completeness",
        ]
        # Auto-include faithfulness & context_relevance if contexts are provided
        if contexts and "faithfulness" not in metrics_to_run:
            metrics_to_run.append("faithfulness")
        if contexts and "context_relevance" not in metrics_to_run:
            metrics_to_run.append("context_relevance")

        results: List[MetricEvaluationResult] = []
        scores_for_average: List[float] = []

        for metric_name in metrics_to_run:
            metric_impl = self._metrics.get(metric_name)
            if not metric_impl:
                continue

            metric_res = metric_impl.evaluate(
                generated_answer=generated_answer,
                question=question,
                reference_answer=reference_answer,
                contexts=contexts,
                metadata=metadata,
            )
            results.append(metric_res)

            # Invert hallucination risk for overall positive quality score (1.0 - risk)
            if metric_name == "hallucination_risk":
                scores_for_average.append(1.0 - metric_res.score)
            else:
                scores_for_average.append(metric_res.score)

        overall_score = (
            round(sum(scores_for_average) / max(1, len(scores_for_average)), 4)
            if scores_for_average
            else 0.0
        )

        # Determine overall verdict
        if overall_score >= 0.70:
            overall_status = MetricStatus.PASS
            summary = f"Evaluation Passed: Composite score {overall_score:.2f} across {len(results)} metrics."
        elif overall_score >= 0.40:
            overall_status = MetricStatus.WARNING
            summary = f"Evaluation Warning: Moderate quality score {overall_score:.2f}. Some metrics flagged variances."
        else:
            overall_status = MetricStatus.FAIL
            summary = f"Evaluation Failed: Low composite score {overall_score:.2f}. Output diverges from expected standards."

        return EvaluationResultResponse(
            overall_score=overall_score,
            summary=summary,
            status=overall_status,
            metrics=results,
            metadata={"evaluated_metrics_count": len(results)},
        )

    async def persist_evaluation(
        self,
        session: AsyncSession,
        execution_id: int,
        evaluation_response: EvaluationResultResponse,
        experiment_id: Optional[int] = None,
    ) -> EvaluationResult:
        """Save evaluation result and individual metric rows into the database."""
        eval_record = EvaluationResult(
            execution_id=execution_id,
            experiment_id=experiment_id,
            overall_score=evaluation_response.overall_score,
            summary=evaluation_response.summary,
            status=evaluation_response.status,
        )
        session.add(eval_record)
        await session.flush()

        for m in evaluation_response.metrics:
            metric_row = EvaluationMetric(
                evaluation_result_id=eval_record.id,
                metric_name=m.metric_name,
                score=m.score,
                score_min=m.score_min,
                score_max=m.score_max,
                explanation=m.explanation,
                status=m.status,
            )
            session.add(metric_row)

        await session.commit()
        await session.refresh(eval_record)
        return eval_record


evaluation_engine = EvaluationEngine()

