# Evaluation Methodology — LLMOps Studio

## 1. Principles of Evaluation

Evaluating Large Language Model applications requires moving beyond generic qualitative observations to rigorous, reproducible, and verifiable quantitative metrics.

LLMOps Studio adheres to the following evaluation engineering principles:
1. **Determinism in Benchmarking**: Offline test runs and CI/CD pipelines must produce deterministic, reproducible evaluations without depending on external closed API services or variable network latencies.
2. **Transparent Formulas**: Every metric calculation is explicitly documented and mathematically formulated.
3. **Clear Boundary of Limitations**: Heuristic indicators must never be misrepresented as definitive factual verifications or infallible hallucination detection.
4. **Structured Verdicts**: Every metric returns a standardized contract:
   - Metric Name
   - Normalized Score ($0.0 \to 1.0$)
   - Score Range
   - Human-readable Explanation
   - Verdict Status (`PASS`, `WARNING`, `FAIL`)
   - Diagnostic Metadata

---

## 2. Implemented Evaluation Metrics

### A. Exact Match (`exact_match`)
Measures literal character and normalized token identity between generated text $G$ and ground truth reference $R$.
- **Strict Match**: $G == R \implies \text{Score} = 1.0$.
- **Normalized Match**: Lowercased, stripped of punctuation, and collapsed whitespace $\implies \text{Score} = 0.95$.
- **Mismatch**: $\text{Score} = 0.0$.

### B. Semantic Similarity (`semantic_similarity`)
Computes composite character and word N-gram TF-IDF cosine distance:
$$\text{Cosine}(\vec{u}, \vec{v}) = \frac{\sum_{i} u_i v_i}{\sqrt{\sum_i u_i^2} \sqrt{\sum_i v_i^2}}$$
- **Unigram Word Cosine** ($w_1 = 0.4$): Captures topical lexical alignment.
- **Bigram Word Cosine** ($w_2 = 0.3$): Captures localized phrasing and compound terminology.
- **Character Trigram Cosine** ($w_3 = 0.3$): Captures subword morphology and spelling variations.
- **Composite Score**: $S = 0.4 \cdot S_{\text{uni}} + 0.3 \cdot S_{\text{bi}} + 0.3 \cdot S_{\text{tri}}$.

### C. Answer Relevance (`answer_relevance`)
Assesses whether the generated response directly answers the user's question $Q$:
- **Keyword Recall**: Proportion of essential non-stopword tokens from $Q$ addressed in $G$.
- **Semantic Intent Alignment**: Cosine distance between question token frequency vector and answer frequency vector.
- **Length Penalty**: Penalizes degenerate outputs (< 4 words).
$$S = (0.6 \cdot \text{Recall} + 0.4 \cdot \text{Cosine}) \times \text{LengthPenalty}$$

### D. Context Relevance (`context_relevance`)
Measures the signal-to-noise ratio in retrieved context passages $C = \{c_1, c_2, \dots, c_k\}$ relative to the user query $Q$:
- Computes sentence-level query keyword coverage per context chunk $c_i$.
- Evaluates the fraction of retrieved passages exceeding relevance thresholds.

### E. Faithfulness / Groundedness (`faithfulness`)
Measures factual consistency of generated response $G$ against supplied contexts $C$:
1. Decomposes $G$ into individual atomic declarative statements $S = \{s_1, s_2, \dots, s_m\}$.
2. For each statement $s_j$, verifies whether its core content words are supported by the context corpus.
3. Formulates the Groundedness Ratio:
$$\text{Faithfulness} = \frac{\text{Count of Grounded Statements}}{\text{Total Statements}}$$
4. Flags ungrounded statements for root-cause inspection.

### F. Response Completeness (`completeness`)
Assesses whether the generated response covers the necessary factual points specified in reference answer $R$:
$$\text{Completeness} = 0.7 \cdot \text{Recall}(K_R \cap K_G) + 0.3 \cdot \min\left(1.0, \frac{\text{len}(G)}{\text{len}(R)}\right)$$

### G. Hallucination Risk Indicators (`hallucination_risk`)
Inspects the generated response for factual anchors that do not exist in the context:
- Extracted Entities: Numbers, percentages, currency, dates, and capitalized named entities.
- Identifies entities in $G$ not found in $C$.
- Detects contradiction transition cues (e.g., "contrary to context", "incorrectly stated").
- Computes Risk Index ($0.0 \to 1.0$).
> **Limitation Note**: Heuristic risk indicators provide early anomaly alerts. They do not replace formal natural language inference (NLI) models, external knowledge graphs, or human domain expert audits.

---

## 3. RAGAS Architectural Compatibility

LLMOps Studio implements a RAGAS-compatible architecture:
- Aligned data contracts: `question`, `retrieved_contexts`, `generated_answer`, `reference_answer`.
- The RAG Triad: Context Relevance, Faithfulness, Answer Relevance.
- Clear boundary: LLMOps Studio's native evaluators operate deterministically and offline without requiring external API keys. Custom LLM-as-a-judge pipelines or official RAGAS Python SDK packages can be plugged into the modular `BaseEvaluationMetric` interface.

