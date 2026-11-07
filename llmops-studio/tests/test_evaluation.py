"""Tests for Evaluation Metrics and Evaluation Engine."""
from app.evaluation.completeness import ResponseCompletenessMetric
from app.evaluation.engine import evaluation_engine
from app.evaluation.exact_match import ExactMatchMetric
from app.evaluation.faithfulness import FaithfulnessMetric
from app.evaluation.hallucination import HallucinationRiskMetric
from app.evaluation.relevance import AnswerRelevanceMetric, ContextRelevanceMetric
from app.evaluation.semantic_similarity import SemanticSimilarityMetric
from app.models.enums import MetricStatus


def test_exact_match_metric():
    """Verify strict, normalized, and mismatched exact match evaluations."""
    metric = ExactMatchMetric()

    # 1. Strict match
    res_strict = metric.evaluate(
        generated_answer="PostgreSQL",
        reference_answer="PostgreSQL",
    )
    assert res_strict.score == 1.0
    assert res_strict.status == MetricStatus.PASS

    # 2. Normalized match (punctuation and casing differences)
    res_norm = metric.evaluate(
        generated_answer="postgresql!",
        reference_answer="PostgreSQL",
    )
    assert res_norm.score == 0.95
    assert res_norm.status == MetricStatus.PASS

    # 3. Mismatch
    res_mismatch = metric.evaluate(
        generated_answer="MongoDB",
        reference_answer="PostgreSQL",
    )
    assert res_mismatch.score == 0.0
    assert res_mismatch.status == MetricStatus.FAIL


def test_semantic_similarity_metric():
    """Verify semantic similarity metric yields high scores for semantically aligned text."""
    metric = SemanticSimilarityMetric()

    # Identical
    res_identical = metric.evaluate(
        generated_answer="Python uses an asynchronous event loop for non-blocking I/O.",
        reference_answer="Python uses an asynchronous event loop for non-blocking I/O.",
    )
    assert res_identical.score == 1.0
    assert res_identical.status == MetricStatus.PASS

    # High semantic overlap
    res_similar = metric.evaluate(
        generated_answer="Asyncio in Python provides an event loop for concurrent asynchronous tasks.",
        reference_answer="Python provides an asynchronous event loop to handle concurrent coroutines.",
    )
    assert res_similar.score > 0.50

    # Divergent / unrelated
    res_divergent = metric.evaluate(
        generated_answer="French cooking emphasizes butter, cream, and delicate wine reductions.",
        reference_answer="Python provides an asynchronous event loop to handle concurrent coroutines.",
    )
    assert res_divergent.score < 0.30


def test_answer_relevance_metric():
    """Verify answer relevance checks question keyword coverage."""
    metric = AnswerRelevanceMetric()

    # Relevant answer
    res_rel = metric.evaluate(
        generated_answer="A B-Tree index maintains sorted keys to guarantee O(log N) lookup time in relational databases.",
        question="What is the time complexity of a B-Tree index search?",
    )
    assert res_rel.score >= 0.50
    assert res_rel.status in (MetricStatus.PASS, MetricStatus.WARNING)

    # Irrelevant answer
    res_irrel = metric.evaluate(
        generated_answer="The sun is approximately 93 million miles from Earth.",
        question="What is the time complexity of a B-Tree index search?",
    )
    assert res_irrel.score < 0.30


def test_context_relevance_metric():
    """Verify context relevance checks proportion of relevant passages."""
    metric = ContextRelevanceMetric()

    contexts = [
        "B-Tree indexes provide logarithmic search performance for queries.",
        "PostgreSQL supports multiple indexing methods including B-Tree and GIN.",
    ]
    res = metric.evaluate(
        generated_answer="B-Trees are fast.",
        question="How do B-Tree indexes perform for database search queries?",
        contexts=contexts,
    )
    assert res.score >= 0.40
    assert res.status in (MetricStatus.PASS, MetricStatus.WARNING)


def test_faithfulness_metric():
    """Verify faithfulness detects grounded assertions and flags ungrounded claims."""
    metric = FaithfulnessMetric()

    contexts = [
        "The Eiffel Tower is located in Paris, France. It was completed in 1889 for the World's Fair."
    ]

    # Grounded answer
    grounded_ans = "The Eiffel Tower is in Paris and was completed in 1889 for the World's Fair."
    res_grounded = metric.evaluate(
        generated_answer=grounded_ans,
        contexts=contexts,
    )
    assert res_grounded.score >= 0.80
    assert res_grounded.status == MetricStatus.PASS

    # Hallucinated answer with claims not in context
    hallucinated_ans = "The Eiffel Tower was built by Leonardo da Vinci in Berlin in the year 1450."
    res_hallucinated = metric.evaluate(
        generated_answer=hallucinated_ans,
        contexts=contexts,
    )
    assert res_hallucinated.score < 0.50


def test_response_completeness_metric():
    """Verify completeness assesses coverage of reference answer elements."""
    metric = ResponseCompletenessMetric()

    reference = "Raft ensures consensus using leader election, log replication, and safety guarantees."
    complete_ans = "Raft achieves distributed consensus through leader election, replicated logs, and safety checks."
    incomplete_ans = "Raft is a protocol."

    res_comp = metric.evaluate(generated_answer=complete_ans, reference_answer=reference)
    res_incomp = metric.evaluate(generated_answer=incomplete_ans, reference_answer=reference)

    assert res_comp.score > res_incomp.score
    assert res_comp.score >= 0.60


def test_hallucination_risk_indicator():
    """Verify hallucination risk heuristic flags ungrounded numbers and entities."""
    metric = HallucinationRiskMetric()

    contexts = ["The company reported revenue of $50M in 2023 with 200 employees."]

    # Answer citing matching numbers
    clean_ans = "In 2023, the company generated $50M in revenue."
    res_clean = metric.evaluate(generated_answer=clean_ans, contexts=contexts)
    assert res_clean.score <= 0.25

    # Answer introducing ungrounded numbers and dates
    risky_ans = "In 1999, the company lost $850M and laid off 45000 workers in Tokyo."
    res_risky = metric.evaluate(generated_answer=risky_ans, contexts=contexts)
    assert res_risky.score > 0.50


def test_composite_evaluation_engine():
    """Verify central evaluation engine executes modular suite and computes composite verdict."""
    res = evaluation_engine.evaluate(
        generated_answer="B-Tree indexes provide O(log N) search performance.",
        question="What is the search complexity of a B-Tree?",
        reference_answer="B-Tree indexes provide logarithmic O(log N) time for search operations.",
        contexts=["B-Tree indexes provide O(log N) search complexity in relational databases."],
    )
    assert res.overall_score >= 0.60
    assert len(res.metrics) >= 4
    assert res.status in (MetricStatus.PASS, MetricStatus.WARNING)
