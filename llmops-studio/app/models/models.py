"""SQLAlchemy ORM models for LLMOps Studio."""
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import (
    ErrorCategory,
    ExecutionStatus,
    ExperimentStatus,
    MetricStatus,
    ProviderType,
)


def utc_now() -> datetime:
    """Return current UTC timestamp."""
    return datetime.now(timezone.utc)


class ModelProvider(Base):
    """External or local LLM provider registry entry."""
    __tablename__ = "model_providers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    provider_type: Mapped[ProviderType] = mapped_column(Enum(ProviderType), nullable=False)
    base_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    models: Mapped[List["ModelConfiguration"]] = relationship(
        "ModelConfiguration", back_populates="provider", cascade="all, delete-orphan", lazy="selectin"
    )


class ModelConfiguration(Base):
    """Specific model configuration, default hyperparameters, and capability metadata."""
    __tablename__ = "model_configurations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    provider_id: Mapped[int] = mapped_column(Integer, ForeignKey("model_providers.id", ondelete="CASCADE"), nullable=False, index=True)
    model_identifier: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    default_temperature: Mapped[float] = mapped_column(Float, default=0.7, nullable=False)
    default_max_tokens: Mapped[int] = mapped_column(Integer, default=1024, nullable=False)
    default_top_p: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    timeout_seconds: Mapped[int] = mapped_column(Integer, default=30, nullable=False)

    # Cost tracking (Explicitly nullable: if None, cost is unavailable)
    cost_per_1k_input_tokens: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    cost_per_1k_output_tokens: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    is_available: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    metadata_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    provider: Mapped["ModelProvider"] = relationship("ModelProvider", back_populates="models", lazy="selectin")
    executions: Mapped[List["ModelExecution"]] = relationship("ModelExecution", back_populates="model_config")
    experiment_runs: Mapped[List["ExperimentRun"]] = relationship("ExperimentRun", back_populates="model_config")


class Prompt(Base):
    """Prompt template container with version history."""
    __tablename__ = "prompts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(150), unique=True, nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tags: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    versions: Mapped[List["PromptVersion"]] = relationship(
        "PromptVersion", back_populates="prompt", cascade="all, delete-orphan", order_by="desc(PromptVersion.version_number)", lazy="selectin"
    )


class PromptVersion(Base):
    """Immutable version of a prompt template."""
    __tablename__ = "prompt_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    prompt_id: Mapped[int] = mapped_column(Integer, ForeignKey("prompts.id", ondelete="CASCADE"), nullable=False, index=True)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    template_text: Mapped[str] = mapped_column(Text, nullable=False)
    input_variables: Mapped[str] = mapped_column(Text, default="[]", nullable=False)  # JSON array string
    system_prompt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    prompt: Mapped["Prompt"] = relationship("Prompt", back_populates="versions")
    executions: Mapped[List["ModelExecution"]] = relationship("ModelExecution", back_populates="prompt_version")
    experiments: Mapped[List["Experiment"]] = relationship("Experiment", back_populates="prompt_version")

    __table_args__ = (
        Index("idx_prompt_version", "prompt_id", "version_number", unique=True),
    )


class Dataset(Base):
    """Evaluation dataset header."""
    __tablename__ = "datasets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(150), unique=True, nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    format: Mapped[str] = mapped_column(String(20), default="json", nullable=False)
    record_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    metadata_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    records: Mapped[List["DatasetRecord"]] = relationship(
        "DatasetRecord", back_populates="dataset", cascade="all, delete-orphan", order_by="DatasetRecord.record_index", lazy="selectin"
    )
    experiments: Mapped[List["Experiment"]] = relationship("Experiment", back_populates="dataset")


class DatasetRecord(Base):
    """Individual test sample within a dataset."""
    __tablename__ = "dataset_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    dataset_id: Mapped[int] = mapped_column(Integer, ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False, index=True)
    record_index: Mapped[int] = mapped_column(Integer, nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    reference_answer: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    contexts: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON array string of retrieved contexts
    metadata_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    dataset: Mapped["Dataset"] = relationship("Dataset", back_populates="records")
    executions: Mapped[List["ModelExecution"]] = relationship("ModelExecution", back_populates="dataset_record")

    __table_args__ = (
        Index("idx_dataset_record", "dataset_id", "record_index", unique=True),
    )


class Experiment(Base):
    """Configured multi-model evaluation experiment."""
    __tablename__ = "experiments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    dataset_id: Mapped[int] = mapped_column(Integer, ForeignKey("datasets.id"), nullable=False, index=True)
    prompt_version_id: Mapped[int] = mapped_column(Integer, ForeignKey("prompt_versions.id"), nullable=False, index=True)
    generation_parameters: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON string
    status: Mapped[ExperimentStatus] = mapped_column(Enum(ExperimentStatus), default=ExperimentStatus.PENDING, nullable=False)

    total_runs: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completed_runs: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed_runs: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    dataset: Mapped["Dataset"] = relationship("Dataset", back_populates="experiments", lazy="selectin")
    prompt_version: Mapped["PromptVersion"] = relationship("PromptVersion", back_populates="experiments", lazy="selectin")
    runs: Mapped[List["ExperimentRun"]] = relationship("ExperimentRun", back_populates="experiment", cascade="all, delete-orphan", lazy="selectin")
    executions: Mapped[List["ModelExecution"]] = relationship("ModelExecution", back_populates="experiment")


class ExperimentRun(Base):
    """Sub-run for a specific model within an experiment."""
    __tablename__ = "experiment_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    experiment_id: Mapped[int] = mapped_column(Integer, ForeignKey("experiments.id", ondelete="CASCADE"), nullable=False, index=True)
    model_config_id: Mapped[int] = mapped_column(Integer, ForeignKey("model_configurations.id"), nullable=False, index=True)
    status: Mapped[ExperimentStatus] = mapped_column(Enum(ExperimentStatus), default=ExperimentStatus.PENDING, nullable=False)
    run_index: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    latency_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    experiment: Mapped["Experiment"] = relationship("Experiment", back_populates="runs")
    model_config: Mapped["ModelConfiguration"] = relationship("ModelConfiguration", back_populates="experiment_runs", lazy="selectin")
    executions: Mapped[List["ModelExecution"]] = relationship("ModelExecution", back_populates="experiment_run")


class ModelExecution(Base):
    """Single prompt/model invocation telemetry record."""
    __tablename__ = "model_executions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    request_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    experiment_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("experiments.id", ondelete="SET NULL"), nullable=True, index=True)
    experiment_run_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("experiment_runs.id", ondelete="SET NULL"), nullable=True, index=True)
    model_config_id: Mapped[int] = mapped_column(Integer, ForeignKey("model_configurations.id"), nullable=False, index=True)
    prompt_version_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("prompt_versions.id", ondelete="SET NULL"), nullable=True)
    dataset_record_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("dataset_records.id", ondelete="SET NULL"), nullable=True)

    input_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    output_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[ExecutionStatus] = mapped_column(Enum(ExecutionStatus), default=ExecutionStatus.SUCCESS, nullable=False, index=True)
    error_category: Mapped[ErrorCategory] = mapped_column(Enum(ErrorCategory), default=ErrorCategory.NONE, nullable=False, index=True)
    error_details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    latency_ms: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    input_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    generation_parameters: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON string
    cost_estimate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)

    model_config: Mapped["ModelConfiguration"] = relationship("ModelConfiguration", back_populates="executions", lazy="selectin")
    prompt_version: Mapped[Optional["PromptVersion"]] = relationship("PromptVersion", back_populates="executions", lazy="selectin")
    dataset_record: Mapped[Optional["DatasetRecord"]] = relationship("DatasetRecord", back_populates="executions", lazy="selectin")
    experiment: Mapped[Optional["Experiment"]] = relationship("Experiment", back_populates="executions")
    experiment_run: Mapped[Optional["ExperimentRun"]] = relationship("ExperimentRun", back_populates="executions")
    evaluation_results: Mapped[List["EvaluationResult"]] = relationship("EvaluationResult", back_populates="execution", cascade="all, delete-orphan", lazy="selectin")
    logs: Mapped[List["ExecutionLog"]] = relationship("ExecutionLog", back_populates="execution", cascade="all, delete-orphan", lazy="selectin")


class EvaluationResult(Base):
    """Aggregated evaluation verdict for a model execution."""
    __tablename__ = "evaluation_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    execution_id: Mapped[int] = mapped_column(Integer, ForeignKey("model_executions.id", ondelete="CASCADE"), nullable=False, index=True)
    experiment_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("experiments.id", ondelete="SET NULL"), nullable=True, index=True)

    overall_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[MetricStatus] = mapped_column(Enum(MetricStatus), default=MetricStatus.PASS, nullable=False)
    metadata_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    execution: Mapped["ModelExecution"] = relationship("ModelExecution", back_populates="evaluation_results")
    metrics: Mapped[List["EvaluationMetric"]] = relationship("EvaluationMetric", back_populates="evaluation_result", cascade="all, delete-orphan", lazy="selectin")


class EvaluationMetric(Base):
    """Granular metric measurement within an evaluation."""
    __tablename__ = "evaluation_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    evaluation_result_id: Mapped[int] = mapped_column(Integer, ForeignKey("evaluation_results.id", ondelete="CASCADE"), nullable=False, index=True)

    metric_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    score_min: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    score_max: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    explanation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[MetricStatus] = mapped_column(Enum(MetricStatus), default=MetricStatus.PASS, nullable=False)
    metadata_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    evaluation_result: Mapped["EvaluationResult"] = relationship("EvaluationResult", back_populates="metrics")


class ExecutionLog(Base):
    """Detailed log line captured during a model invocation lifecycle."""
    __tablename__ = "execution_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    execution_id: Mapped[int] = mapped_column(Integer, ForeignKey("model_executions.id", ondelete="CASCADE"), nullable=False, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    level: Mapped[str] = mapped_column(String(20), default="INFO", nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    execution: Mapped["ModelExecution"] = relationship("ModelExecution", back_populates="logs")
