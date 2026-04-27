from __future__ import annotations

from dataclasses import dataclass
import json
import os
from typing import Any, Protocol
from urllib import request

from pydantic import BaseModel, Field

from baeloop.advisor import propose_patch
from baeloop.advisor_analysis import analyze_report
from baeloop.advisor_critic import critique_intervention
from baeloop.advisor_hypothesis import propose_intervention
from baeloop.models import AdvisorProposal, ComparisonReport, Intervention
from baeloop.patcher import ALLOWED_PATCH_KEYS


class LLMAdvisorError(RuntimeError):
    """Raised when the LLM advisor cannot produce a valid bounded proposal."""


@dataclass(frozen=True)
class LLMAdvisorConfig:
    model: str = "gpt-5.4"
    base_url: str = "https://api.ai.ohfi.com.cn/v1"
    api_key_env: str = "OHFI_API_KEY"
    stream: bool = True
    temperature: float = 0.1
    max_tokens: int = 2048
    timeout_sec: float = 60.0


class ChatClient(Protocol):
    def complete(
        self,
        *,
        stage: str,
        messages: list[dict[str, str]],
        config: LLMAdvisorConfig,
    ) -> str: ...


class LLMStageNote(BaseModel):
    summary: str
    dominant_root_causes: list[str] = Field(default_factory=list)
    key_deltas: list[str] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)


class LLMCriticNote(BaseModel):
    decision: str
    notes: list[str] = Field(default_factory=list)


class OpenAICompatibleChatClient:
    def complete(
        self,
        *,
        stage: str,
        messages: list[dict[str, str]],
        config: LLMAdvisorConfig,
    ) -> str:
        api_key = os.environ.get(config.api_key_env)
        if not api_key:
            raise LLMAdvisorError(f"Missing API key environment variable `{config.api_key_env}`")

        payload: dict[str, Any] = {
            "model": config.model,
            "messages": messages,
            "temperature": config.temperature,
            "max_tokens": config.max_tokens,
            "stream": config.stream,
        }
        body = json.dumps(payload).encode("utf-8")
        endpoint = f"{config.base_url.rstrip('/')}/chat/completions"
        req = request.Request(
            endpoint,
            data=body,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        with request.urlopen(req, timeout=config.timeout_sec) as response:
            if config.stream:
                return _read_streaming_content(response)
            return _read_non_streaming_content(response)


def propose_patch_with_llm(
    report: ComparisonReport,
    config: LLMAdvisorConfig | None = None,
    client: ChatClient | None = None,
) -> AdvisorProposal:
    resolved_config = config or LLMAdvisorConfig()
    resolved_client = client or OpenAICompatibleChatClient()
    deterministic = propose_patch(report)
    analysis = analyze_report(report)
    reference_intervention = propose_intervention(analysis)
    compact_report = _compact_report(report)

    try:
        analyst = _run_analyst(resolved_client, resolved_config, compact_report)
        intervention = _run_hypothesis(
            resolved_client,
            resolved_config,
            compact_report=compact_report,
            analyst=analyst,
            deterministic_intervention=reference_intervention,
        )
        _validate_bounded_patch(intervention)
        proposal = critique_intervention(analysis, intervention)
        critic = _run_critic(
            resolved_client,
            resolved_config,
            compact_report=compact_report,
            analyst=analyst,
            proposal=proposal,
        )
        proposal = _apply_llm_critic(proposal, critic)
        proposal.advisor_mode = "llm"
        proposal.advisor_stage_notes = {
            "analyst": analyst.model_dump(mode="json"),
            "critic": critic.model_dump(mode="json"),
        }
        return proposal
    except Exception as exc:
        deterministic.advisor_mode = "llm_fallback"
        deterministic.critic_notes.append(f"llm advisor fallback: {type(exc).__name__}")
        deterministic.advisor_stage_notes = {"fallback_error": str(exc)}
        return deterministic


def _run_analyst(
    client: ChatClient,
    config: LLMAdvisorConfig,
    compact_report: dict[str, Any],
) -> LLMStageNote:
    content = client.complete(
        stage="analyst",
        config=config,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are the Analyst Agent for BAELOOP. Read browser-agent "
                    "experiment evidence and return JSON only. Do not propose patches."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "schema": {
                            "summary": "string",
                            "dominant_root_causes": ["string"],
                            "key_deltas": ["string"],
                            "risk_flags": ["string"],
                        },
                        "report": compact_report,
                    },
                    sort_keys=True,
                ),
            },
        ],
    )
    return LLMStageNote.model_validate(_extract_json_object(content))


def _run_hypothesis(
    client: ChatClient,
    config: LLMAdvisorConfig,
    *,
    compact_report: dict[str, Any],
    analyst: LLMStageNote,
    deterministic_intervention: Intervention,
) -> Intervention:
    content = client.complete(
        stage="hypothesis",
        config=config,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are the Hypothesis Agent for BAELOOP. Return JSON only "
                    "matching the Intervention schema. Prefer hold/investigation "
                    "when evidence is not enough. Any patch must be bounded."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "allowed_patch_keys": sorted(ALLOWED_PATCH_KEYS),
                        "intervention_schema": {
                            "id": "string",
                            "kind": "config_patch|retry_policy|action_policy|observation_policy|hold|investigation",
                            "summary": "string",
                            "rationale": "string",
                            "expected_effect": "string",
                            "risk": "string",
                            "patch": {},
                            "target_root_causes": ["string"],
                            "supported_by": ["string"],
                        },
                        "analyst": analyst.model_dump(mode="json"),
                        "deterministic_reference": deterministic_intervention.model_dump(mode="json"),
                        "report": compact_report,
                    },
                    sort_keys=True,
                ),
            },
        ],
    )
    return Intervention.model_validate(_extract_json_object(content))


def _run_critic(
    client: ChatClient,
    config: LLMAdvisorConfig,
    *,
    compact_report: dict[str, Any],
    analyst: LLMStageNote,
    proposal: AdvisorProposal,
) -> LLMCriticNote:
    content = client.complete(
        stage="critic",
        config=config,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are the Critic Agent for BAELOOP. Return JSON only. "
                    "Reject unsupported or unbounded patch-bearing proposals."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "schema": {"decision": "accepted|rejected", "notes": ["string"]},
                        "allowed_patch_keys": sorted(ALLOWED_PATCH_KEYS),
                        "analyst": analyst.model_dump(mode="json"),
                        "proposal": proposal.model_dump(mode="json"),
                        "report": compact_report,
                    },
                    sort_keys=True,
                ),
            },
        ],
    )
    note = LLMCriticNote.model_validate(_extract_json_object(content))
    if note.decision not in {"accepted", "rejected"}:
        raise LLMAdvisorError(f"Invalid critic decision: {note.decision}")
    return note


def _apply_llm_critic(proposal: AdvisorProposal, critic: LLMCriticNote) -> AdvisorProposal:
    notes = [f"llm critic: {note}" for note in critic.notes]
    proposal.critic_notes.extend(notes)
    if critic.decision == "rejected":
        proposal.patch = {}
        proposal.critic_decision = "rejected"
    return proposal


def _validate_bounded_patch(intervention: Intervention) -> None:
    unknown_keys = set(intervention.patch) - ALLOWED_PATCH_KEYS
    if unknown_keys:
        raise LLMAdvisorError(f"Unsupported LLM patch keys: {sorted(unknown_keys)}")
    if intervention.kind in {"config_patch", "retry_policy", "action_policy", "observation_policy"}:
        if not intervention.patch:
            raise LLMAdvisorError("Patch-bearing LLM intervention omitted patch")


def _compact_report(report: ComparisonReport) -> dict[str, Any]:
    return {
        "baseline_config_id": report.baseline_config_id,
        "candidate_config_id": report.candidate_config_id,
        "taskset_id": report.taskset_id,
        "compared_task_count": report.compared_task_count,
        "regression_count": report.regression_count,
        "improvement_count": len(report.improvements),
        "metrics": _jsonable(report.metrics),
        "failure_summary": report.failure_summary,
        "failure_evidence": _jsonable(report.failure_evidence),
        "regressions": _jsonable(report.regressions),
        "improvements": _jsonable(report.improvements),
    }


def _jsonable(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    return value


def _extract_json_object(content: str) -> dict[str, Any]:
    stripped = content.strip()
    if stripped.startswith("```"):
        stripped = stripped.strip("`")
        if stripped.startswith("json"):
            stripped = stripped[4:].strip()
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start < 0 or end < start:
        raise LLMAdvisorError("LLM response did not contain a JSON object")
    return json.loads(stripped[start : end + 1])


def _read_non_streaming_content(response: Any) -> str:
    payload = json.loads(response.read().decode("utf-8"))
    return payload["choices"][0]["message"]["content"]


def _read_streaming_content(response: Any) -> str:
    chunks: list[str] = []
    for raw_line in response:
        line = raw_line.decode("utf-8").strip()
        if not line or not line.startswith("data:"):
            continue
        data = line.removeprefix("data:").strip()
        if data == "[DONE]":
            break
        payload = json.loads(data)
        delta = payload.get("choices", [{}])[0].get("delta", {})
        if isinstance(delta.get("content"), str):
            chunks.append(delta["content"])
    return "".join(chunks)
