from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


RunStatus = Literal["success", "failed", "timeout", "error", "max_steps"]
InterventionKind = Literal[
    "config_patch",
    "retry_policy",
    "action_policy",
    "observation_policy",
    "hold",
    "investigation",
]
CriticDecision = Literal["accepted", "rejected"]


class RetryPolicy(BaseModel):
    enabled: bool = False
    max_retries: int = Field(default=0, ge=0)


class ActionPolicyConfig(BaseModel):
    enabled: bool = False
    name: str = "none"
    policies: list[str] = Field(default_factory=list)
    max_interventions: int = Field(default=0, ge=0)
    policy_limits: dict[str, int] = Field(default_factory=dict)
    scroll_delta_y: int = 621


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
    action_policy: ActionPolicyConfig = Field(default_factory=ActionPolicyConfig)
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
    diagnostics: dict[str, int | float | str | bool] = Field(default_factory=dict)


class MetricSummary(BaseModel):
    task_count: int
    success_rate: float
    avg_normalized_score: float
    avg_step_count: float
    avg_latency_sec: float
    avg_input_tokens: float = 0.0
    avg_output_tokens: float = 0.0
    avg_llm_call_count: float = 0.0
    avg_agent_retry_count: float = 0.0
    avg_busted_retry_count: float = 0.0
    avg_action_policy_interventions: float = 0.0
    failure_taxonomy: dict[str, int]


class TaskDelta(BaseModel):
    task_id: str
    baseline_status: RunStatus
    candidate_status: RunStatus
    baseline_score: float
    candidate_score: float
    score_delta: float


class FailureEvidence(BaseModel):
    task_id: str
    failure_type: str
    root_cause: str
    confidence: str
    evidence: list[str] = Field(default_factory=list)
    suggested_action: str


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
    failure_evidence: dict[str, list[FailureEvidence]] = Field(default_factory=dict)


class AdvisorAnalysis(BaseModel):
    baseline_failures: dict[str, int]
    baseline_root_causes: dict[str, int]
    candidate_failures: dict[str, int]
    candidate_root_causes: dict[str, int]
    dominant_failure: str | None = None
    dominant_root_cause: str | None = None
    quality_not_worse: bool
    efficiency_gain: bool
    success_rate_delta: float
    avg_score_delta: float
    regression_count: int
    evidence_count: int


class Intervention(BaseModel):
    id: str
    kind: InterventionKind
    summary: str
    rationale: str
    expected_effect: str
    risk: str
    patch: dict[str, Any] = Field(default_factory=dict)
    target_root_causes: list[str] = Field(default_factory=list)
    supported_by: list[str] = Field(default_factory=list)


class AdvisorProposal(BaseModel):
    hypothesis_id: str
    summary: str
    rationale: str
    expected_effect: str
    risk: str
    patch: dict[str, Any]
    intervention: Intervention | None = None
    critic_decision: CriticDecision = "accepted"
    critic_notes: list[str] = Field(default_factory=list)
    advisor_mode: str = "deterministic"
    advisor_stage_notes: dict[str, Any] = Field(default_factory=dict)


class DependencyProbe(BaseModel):
    module: str
    available: bool
    note: str | None = None


class EnvironmentReport(BaseModel):
    adapter: str
    ready: bool
    dependencies: list[DependencyProbe]
