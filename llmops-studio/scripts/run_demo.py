"""Interactive command-line demonstration for LLMOps Studio."""
import asyncio
from pathlib import Path
import sys

root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

from app.evaluation.engine import evaluation_engine
from app.evaluation.rag_evaluator import rag_evaluator
from app.providers.mock import MockProvider
from app.schemas.evaluation import RAGEvaluationRequest
from app.schemas.provider import GenerationParameters


async def main():
    print("=" * 70)
    print("  LLMOps Studio - Interactive Evaluation & Observability Demo")
    print("=" * 70)

    # 1. Provider execution
    print("\n[Step 1] Initializing Deterministic Mock Provider...")
    provider = MockProvider()

    context = (
        "B-Tree indexes maintain sorted balanced trees to guarantee O(log N) lookup "
        "and range scan performance in transactional database engines."
    )
    question = "What time complexity does a B-Tree index provide for search queries?"
    prompt = f"Context: {context}\n\nQuestion: {question}"

    print(f"-> Generating response for question: '{question}'...")
    result = await provider.generate(
        prompt=prompt,
        model="mock-deterministic",
        params=GenerationParameters(temperature=0.0, max_tokens=100),
    )

    print(f"Generated Answer:\n  \"{result.output_text}\"")
    print(f"Latency: {result.latency_ms:.2f}ms | Tokens: {result.total_tokens} (Input: {result.input_tokens}, Output: {result.output_tokens})")

    # 2. Comprehensive Evaluation
    print("\n[Step 2] Executing Modular Evaluation Metrics...")
    ref_answer = "A B-Tree index provides logarithmic O(log N) search performance."
    eval_result = evaluation_engine.evaluate(
        generated_answer=result.output_text,
        question=question,
        reference_answer=ref_answer,
        contexts=[context],
    )

    print(f"Overall Quality Score: {eval_result.overall_score:.3f} | Status: {eval_result.status.value}")
    print(f"Summary: {eval_result.summary}")
    print("\nMetric Breakdown:")
    for m in eval_result.metrics:
        print(f"  * {m.metric_name:<22} Score: {m.score:<5.2f} [{m.status.value:<7}] - {m.explanation}")

    # 3. Dedicated RAG Triad Assessment
    print("\n[Step 3] Running Dedicated RAG Triad Assessment...")
    rag_req = RAGEvaluationRequest(
        question=question,
        retrieved_contexts=[context],
        generated_answer=result.output_text,
        reference_answer=ref_answer,
    )
    rag_res = rag_evaluator.evaluate_pipeline(rag_req)
    triad = rag_res.triad_scores
    print(f"  - Context Relevance : {triad.context_relevance:.2f}")
    print(f"  - Faithfulness       : {triad.faithfulness:.2f}")
    print(f"  - Answer Relevance   : {triad.answer_relevance:.2f}")
    print(f"  - Context Coverage   : {triad.context_coverage:.2f}")
    print(f"  -> Composite RAG     : {triad.overall_rag_score:.2f}")
    print(f"  - Hallucination Flag : {rag_res.hallucination_detected} (Risk: {rag_res.hallucination_risk_score:.2f})")

    print("\n" + "=" * 70)
    print("  LLMOps Studio demonstration completed successfully!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())

