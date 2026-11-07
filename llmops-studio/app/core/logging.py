"""Structured logging configuration for LLMOps Studio."""
import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any, Dict


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured observability logs."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "line": record.lineno,
        }
        if hasattr(record, "request_id"):
            log_entry["request_id"] = record.request_id
        if hasattr(record, "experiment_id"):
            log_entry["experiment_id"] = record.experiment_id
        if hasattr(record, "model"):
            log_entry["model"] = record.model
        if hasattr(record, "latency_ms"):
            log_entry["latency_ms"] = record.latency_ms
        if hasattr(record, "tokens"):
            log_entry["tokens"] = record.tokens
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_entry)


def setup_logging(level: str = "INFO", structured: bool = True) -> logging.Logger:
    """Configure root logger with console and optional JSON formatting."""
    root_logger = logging.getLogger("llmops_studio")
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Remove existing handlers if any
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    handler = logging.StreamHandler(sys.stdout)
    if structured:
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(
            logging.Formatter(
                "[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s"
            )
        )
    root_logger.addHandler(handler)
    return root_logger


logger = setup_logging()

