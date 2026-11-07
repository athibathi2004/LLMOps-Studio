# REST API Reference — LLMOps Studio

Base Path: `/api/v1`

Interactive Swagger OpenAPI UI: `http://localhost:8000/docs`
ReDoc Specification: `http://localhost:8000/redoc`

---

## 1. System Health

### `GET /api/v1/health`
Checks backend service readiness and database connectivity.
- **Response `200 OK`**:
  ```json
  {
    "status": "healthy",
    "service": "LLMOps Studio",
    "version": "1.0.0",
    "database": "connected",
    "timestamp": "2026-11-07T12:00:00.000000+00:00"
  }
  ```

---

## 2. Models & Providers

### `GET /api/v1/models`
List all registered model configurations.
- **Query Parameters**: `available_only` (bool, default: false).

### `POST /api/v1/models/register`
Register a new model configuration.
- **Request Body**:
  ```json
  {
    "provider_name": "Mock",
    "model_identifier": "mock-deterministic",
    "display_name": "Deterministic Mock Engine",
    "description": "Standard deterministic mock model for benchmarking",
    "default_temperature": 0.0,
    "default_max_tokens": 1024,
    "cost_per_1k_input_tokens": 0.005,
    "cost_per_1k_output_tokens": 0.015
  }
  ```
- **Response `201 Created`**: Returns registered `ModelConfigResponse`.

### `GET /api/v1/models/{model_id}`
Fetch model details by ID.

### `GET /api/v1/models/{model_id}/health`
Live connectivity and latency ping check for the model's provider endpoint.

---

## 3. Prompts & Templates

### `GET /api/v1/prompts`
List all prompt template containers.

### `POST /api/v1/prompts`
Create a new prompt template container and its first version.

### `GET /api/v1/prompts/{prompt_id}`
Get prompt with complete version history.

### `POST /api/v1/prompts/{prompt_id}/versions`
Append an incremented version to an existing prompt template.

### `POST /api/v1/prompts/{prompt_id}/execute`
Execute prompt template with dynamic variable interpolation and record telemetry.

---

## 4. Datasets

### `GET /api/v1/datasets`
List evaluation datasets.

### `POST /api/v1/datasets`
Create evaluation dataset with test case records.

### `GET /api/v1/datasets/{dataset_id}`
Get dataset details and test cases.

### `POST /api/v1/datasets/upload`
Upload multipart form file (JSON or CSV) and ingest as an evaluation dataset.

---

## 5. Experiments

### `GET /api/v1/experiments`
List all experiments.

### `POST /api/v1/experiments`
Create a new multi-model evaluation experiment.

### `GET /api/v1/experiments/{experiment_id}`
Get experiment configuration and sub-run progress.

### `POST /api/v1/experiments/{experiment_id}/run`
Trigger asynchronous execution of experiment across models and dataset test cases.

### `GET /api/v1/experiments/{experiment_id}/results`
Get full execution traces, model summaries, and individual metric results.

### `GET /api/v1/experiments/{experiment_id}/comparison`
Side-by-side benchmark comparison across models.

---

## 6. Evaluations

### `POST /api/v1/evaluations/run`
Run ad-hoc modular evaluation metrics on an input pair.

### `POST /api/v1/evaluations/rag`
Execute dedicated RAG Triad assessment (Context Relevance, Faithfulness, Answer Relevance, Context Coverage, Hallucination Risk).

### `GET /api/v1/evaluations/{evaluation_id}`
Retrieve stored evaluation result and individual metric scores.

---

## 7. Observability & Traces

### `GET /api/v1/executions`
List chronological execution traces with filters (`model_id`, `status`, `error_category`, `experiment_id`, `limit`, `offset`).

### `GET /api/v1/executions/{execution_id}`
Get full execution trace including raw prompt, completion, latency, tokens, cost, evaluation results, and audit logs.

---

## 8. Analytics

### `GET /api/v1/analytics/overview`
High-level KPI metrics (total experiments, executions, avg score, avg latency, tokens, success rate).

### `GET /api/v1/analytics/models`
Per-model performance rankings and quality averages.

### `GET /api/v1/analytics/performance`
Latency trend timelines, evaluation score distribution histogram, and token consumption charts.

### `GET /api/v1/analytics/failures`
Failure categorization breakdown, error counts, and recent failure diagnostics.

