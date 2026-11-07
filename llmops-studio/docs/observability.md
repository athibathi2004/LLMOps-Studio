# Observability & Trace Telemetry — LLMOps Studio

## 1. Observability Architecture

Observability in LLMOps Studio captures granular telemetry for every model invocation across prompt studio runs, automated experiment batches, and ad-hoc evaluations.

### Telemetry Attributes Captured
For every execution, the platform records:
- **`request_id`**: Globally unique UUID identifying the request trace.
- **`experiment_id` & `experiment_run_id`**: Foreign keys correlating batch executions.
- **`model_config_id`**: Precise model configuration and hyperparameters.
- **`start_time` & `end_time`**: ISO 8601 UTC timestamps.
- **`latency_ms`**: Measured via monotonic high-resolution timer (`time.perf_counter()`).
- **`input_tokens`**: Tokens consumed by system prompt and user input.
- **`output_tokens`**: Tokens generated in completion.
- **`total_tokens`**: Input + output tokens.
- **`status`**: `SUCCESS`, `FAILED`, `TIMEOUT`, `EMPTY_RESPONSE`, `CANCELLED`.
- **`error_category`**: Standardized root-cause classification.
- **`cost_estimate`**: Real currency calculation based on model configuration pricing.
- **`input_prompt` & `output_text`**: Full raw text content for reproduction and debugging.

---

## 2. Failure Categorization & Diagnostics

Failures are systematically categorized to pinpoint infrastructure vs. model behavior issues:
| Error Category | Typical Root Cause |
| :--- | :--- |
| `TIMEOUT` | Model inference exceeded specified `timeout_seconds`. |
| `PROVIDER_UNAVAILABLE` | Connection refused, host unreachable, or upstream 503 error. |
| `EMPTY_RESPONSE` | Model returned 0 completion tokens or blank whitespace. |
| `MALFORMED_OUTPUT` | Output failed structured validation or JSON parsing. |
| `EVALUATION_ERROR` | An evaluation metric failed execution. |
| `CONFIGURATION_ERROR` | Requested model identifier not found or unsupported parameters. |
| `UNKNOWN` | Unclassified runtime exception. |

---

## 3. Structured Logging

Structured JSON logging (`app/core/logging.py`) emits standardized log records:
```json
{
  "timestamp": "2026-11-07T12:00:00.000000+00:00",
  "level": "INFO",
  "logger": "llmops_studio",
  "message": "Execution finished on 'Meta Llama 3'. Status=SUCCESS, Latency=45.2ms, Tokens=115.",
  "request_id": "8a3e7b1a-03df-404f-9e79-3fb769b76e1a",
  "latency_ms": 45.2,
  "tokens": 115
}
```
All logs are simultaneously indexed in the database `execution_logs` table and accessible via the **Observability & Traces** UI inspector.

