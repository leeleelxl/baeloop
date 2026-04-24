from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


RunStatus = Literal["success", "failed", "timeout", "error", "max_steps"]


class RetryPolicy(BaseModel):
    enabled: bool = False
    max_retries: int = Field(default=0, ge=0)


class AgentConfig(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    agent: str = "agentlab_generic"
    model: str
    api_base_url: str | None = None
    api_key_env: str | None = None
    prompt_version: str = "v1"
    max_steps: int = Field(gt=0)
    retry_policy: RetryPolicy = Field(default_factory=RetryPolicy)
    observation_mode: str = "text"


class TaskSpec(BaseModel):
    env_id: str
    seed: int
    max_steps: int = Field(gt=0)

    @property
    def task_id(self) -> str:
        return f"{self.env_id}#seed={self.seed}"


class TaskSet(BaseModel):
    id: str
    benchmark: str
    tasks: list[TaskSpec] = Field(min_length=1)


class RunRecord(BaseModel):
    experiment_id: str
    config_id: str
    task_id: str
    status: RunStatus
    normalized_score: float = Field(ge=0.0, le=1.0)
    step_count: int = Field(ge=0)
    latency_sec: float = Field(ge=0.0)
    failure_type: str | None = None
    error: str | None = None


class MetricSummary(BaseModel):
    task_count: int
    success_rate: float
    avg_normalized_score: float
    avg_step_count: float
    avg_latency_sec: float
    failure_taxonomy: dict[str, int]


class TaskDelta(BaseModel):
    task_id: str
    baseline_status: RunStatus
    candidate_status: RunStatus
    baseline_score: float
    candidate_score: float
    score_delta: float


class ComparisonReport(BaseModel):
    baseline_config_id: str
    candidate_config_id: str
    taskset_id: str
    compared_task_count: int
    missing_in_baseline: list[str]
    missing_in_candidate: list[str]
    metrics: dict[str, MetricSummary | dict[str, float]]
    regression_count: int
    regressions: list[TaskDelta]
    improvements: list[TaskDelta]
    failure_summary: dict[str, dict[str, int]]


class AdvisorProposal(BaseModel):
    hypothesis_id: str
    summary: str
    rationale: str
    expected_effect: str
    risk: str
    patch: dict[str, Any]


class DependencyProbe(BaseModel):
    module: str
    available: bool
    note: str | None = None


class EnvironmentReport(BaseModel):
    adapter: str
    ready: bool
    dependencies: list[DependencyProbe]
