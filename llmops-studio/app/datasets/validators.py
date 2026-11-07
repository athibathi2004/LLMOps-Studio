"""Dataset validation and ingestion parsers for JSON and CSV formats."""
import csv
import io
import json
from typing import Any, Dict, List


def validate_dataset_records(raw_records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Validate and normalize a list of raw evaluation test cases."""
    if not raw_records:
        raise ValueError("Dataset cannot be empty. At least one record is required.")

    validated = []
    for idx, rec in enumerate(raw_records):
        if not isinstance(rec, dict):
            raise ValueError(f"Record at index {idx} must be a JSON object / dictionary.")

        # Find question / query / prompt
        question = (
            rec.get("question")
            or rec.get("query")
            or rec.get("prompt")
            or rec.get("input")
        )
        if not question or not str(question).strip():
            raise ValueError(f"Record {idx + 1} is missing required 'question' field.")

        # Reference answer (optional)
        ref_answer = (
            rec.get("reference_answer")
            or rec.get("ground_truth")
            or rec.get("expected_answer")
            or rec.get("target")
        )
        ref_answer_str = str(ref_answer).strip() if ref_answer is not None else None

        # Contexts (optional list of strings or single string)
        raw_ctx = (
            rec.get("contexts")
            or rec.get("context")
            or rec.get("retrieved_contexts")
            or rec.get("documents")
        )
        contexts_list: List[str] = []
        if isinstance(raw_ctx, list):
            contexts_list = [str(c).strip() for c in raw_ctx if str(c).strip()]
        elif isinstance(raw_ctx, str) and raw_ctx.strip():
            # Check if it's a JSON array string
            if raw_ctx.strip().startswith("[") and raw_ctx.strip().endswith("]"):
                try:
                    parsed = json.loads(raw_ctx)
                    if isinstance(parsed, list):
                        contexts_list = [str(c).strip() for c in parsed if str(c).strip()]
                except Exception:
                    contexts_list = [c.strip() for c in raw_ctx.split("|||") if c.strip()]
            else:
                contexts_list = [c.strip() for c in raw_ctx.split("|||") if c.strip()]

        validated.append({
            "record_index": idx + 1,
            "question": str(question).strip(),
            "reference_answer": ref_answer_str,
            "contexts": contexts_list,
            "metadata": rec.get("metadata", {}),
        })

    return validated


def parse_csv_dataset(csv_text: str) -> List[Dict[str, Any]]:
    """Parse CSV text into structured record dictionaries."""
    reader = csv.DictReader(io.StringIO(csv_text))
    raw_records = []
    for row in reader:
        raw_records.append(dict(row))
    return validate_dataset_records(raw_records)


def parse_json_dataset(json_text: str) -> List[Dict[str, Any]]:
    """Parse JSON text into structured record dictionaries."""
    try:
        data = json.loads(json_text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON format: {str(exc)}")

    if isinstance(data, list):
        return validate_dataset_records(data)
    elif isinstance(data, dict):
        if "records" in data and isinstance(data["records"], list):
            return validate_dataset_records(data["records"])
        if "data" in data and isinstance(data["data"], list):
            return validate_dataset_records(data["data"])
        raise ValueError("JSON object must contain a 'records' or 'data' array.")
    else:
        raise ValueError("JSON dataset must be an array of test cases or an object with 'records'.")

