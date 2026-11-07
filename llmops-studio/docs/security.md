# Security, Sandboxing & Reliability — LLMOps Studio

## 1. Security Architecture & Threat Model

LLMOps Studio is architected to safely run evaluation benchmarks and observability traces across untrusted prompt inputs, synthetic datasets, and diverse model endpoints.

### Key Security Controls
1. **No Unrestricted Code Execution**: Prompt templates and variable interpolation avoid `eval`, `exec`, or un-sandboxed Jinja compilation. Variable substitutions are parsed with strict regular expressions and string replacement.
2. **Secret Hygiene**:
   - Zero hardcoded credentials or API keys in the source tree.
   - Provider URLs and secrets are read strictly from environment variables (`.env`).
   - Exception handlers pass error traces through `sanitize_error_message()`, stripping Bearer tokens, API keys, or raw filesystem paths before sending responses to clients.
3. **Bounded Experiment Execution**:
   - Every inference request enforces strict timeouts (`timeout_seconds`, bound between 1s and 120s).
   - Maximum token counts are strictly validated ($1 \le \text{tokens} \le 8192$).
   - Concurrency bounds prevent resource exhaustion.
4. **Dataset Validation & Upload Sanitization**:
   - File uploads in `/api/v1/datasets/upload` are validated for size, mime type, and valid JSON/CSV formatting before ingestion.
   - Control characters and null bytes are stripped via `sanitize_input_text()`.
5. **Database Integrity**:
   - Asynchronous parameterized queries throughout via SQLAlchemy 2.0 ORM prevent SQL injection vulnerabilities.
   - Foreign key constraints are enforced with cascading deletes where appropriate.

---

## 2. Safe Error Handling Architecture

When an unexpected exception occurs, the global exception handler returns sanitized JSON responses:
```json
{
  "detail": "An internal server error occurred.",
  "message": "Ollama request timed out after 30 seconds."
}
```
Internal stack frames are logged securely to the server console and structured logs, but withheld from external API consumers.

