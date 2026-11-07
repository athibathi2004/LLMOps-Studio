# Model Providers Architecture — LLMOps Studio

## 1. Provider Abstraction

LLMOps Studio is designed to be completely provider-agnostic. All interactions with language models flow through the `BaseModelProvider` abstract class defined in `app/providers/base.py`.

```python
class BaseModelProvider(ABC):
    @abstractmethod
    async def generate(
        self,
        prompt: str,
        model: str,
        system_prompt: Optional[str] = None,
        params: Optional[GenerationParameters] = None,
    ) -> ProviderResult:
        pass

    @abstractmethod
    async def check_health(self) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def list_models(self) -> List[str]:
        pass
```

---

## 2. Supported Out-of-the-Box Providers

### A. Deterministic Mock Provider (`app/providers/mock.py`)
Purpose: High-speed local benchmarking, deterministic unit testing, and offline CI/CD test runs without external model servers or API keys.
- **Generation Behavior**: Computes deterministic responses based on prompt keywords and SHA-256 digests.
- **Synthetic Latency**: Simulates non-zero execution duration ($10 \text{--} 25 \text{ ms}$).
- **Token Estimation**: Heuristic word and character tokenizer.
- **Diagnostic Triggers**:
  - `[SIMULATE_TIMEOUT]`: Triggers a timeout exception.
  - `[SIMULATE_EMPTY]`: Returns an empty response string.
  - `[SIMULATE_ERROR]`: Returns an upstream 503 Provider Unavailable error.
  - `[SIMULATE_MALFORMED]`: Returns unclosed JSON structure.

### B. Ollama Provider (`app/providers/ollama.py`)
Purpose: Connects to local or remote open-source LLM instances (Llama 3, Mistral 7B, Gemma 2, etc.) running on Ollama.
- **Endpoint**: Configurable via `OLLAMA_BASE_URL` (default: `http://localhost:11434`).
- **Generation**: Calls `/api/generate` with `stream: false`.
- **Options**: Automatically maps temperature, top-p, and max tokens.
- **Token Telemetry**: Extracts native `prompt_eval_count` and `eval_count`.
- **Error Handling**: Gracefully categorizes connection drops, timeouts, and missing model 404s.

---

## 3. Registering New Models & Custom Providers

To add a new model:
1. Navigate to **Model Registry** in the UI or send a `POST /api/v1/models/register` request.
2. Provide:
   - `provider_name`: e.g., "Ollama" or "Mock"
   - `model_identifier`: e.g., "llama3:8b-instruct"
   - `display_name`: e.g., "Meta Llama 3 8B Instruct"
   - `default_temperature`, `default_max_tokens`, `timeout_seconds`
   - `cost_per_1k_input_tokens`, `cost_per_1k_output_tokens` (set to `null` if running free open-source models).

### Transparent Cost Guarantee
LLMOps Studio strictly enforces honest telemetry:
- If token pricing is configured in the database, cost is calculated as:
  $$\text{Cost} = \frac{\text{Tokens}_{\text{in}}}{1000} \cdot C_{\text{in}} + \frac{\text{Tokens}_{\text{out}}}{1000} \cdot C_{\text{out}}$$
- If pricing is `null`, the cost is explicitly displayed as **Unavailable** rather than fabricating estimates.

