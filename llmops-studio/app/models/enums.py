"""Domain enumeration types for LLMOps Studio."""
from enum import Enum


class ProviderType(str, Enum):
    """Supported model provider categories."""
    MOCK = "MOCK"
    OLLAMA = "OLLAMA"
    OPENAI_COMPATIBLE = "OPENAI_COMPATIBLE"
    CUSTOM = "CUSTOM"


class ExecutionStatus(str, Enum):
    """Lifecycle status of a model execution request."""
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    TIMEOUT = "TIMEOUT"
    EMPTY_RESPONSE = "EMPTY_RESPONSE"
    CANCELLED = "CANCELLED"


class ExperimentStatus(str, Enum):
    """Lifecycle status of an evaluation experiment."""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class MetricStatus(str, Enum):
    """Verdict for an evaluation metric."""
    PASS = "PASS"
    WARNING = "WARNING"
    FAIL = "FAIL"


class ErrorCategory(str, Enum):
    """Categorized root causes for execution and evaluation failures."""
    NONE = "NONE"
    TIMEOUT = "TIMEOUT"
    PROVIDER_UNAVAILABLE = "PROVIDER_UNAVAILABLE"
    EMPTY_RESPONSE = "EMPTY_RESPONSE"
    MALFORMED_OUTPUT = "MALFORMED_OUTPUT"
    EVALUATION_ERROR = "EVALUATION_ERROR"
    CONFIGURATION_ERROR = "CONFIGURATION_ERROR"
    UNKNOWN = "UNKNOWN"

