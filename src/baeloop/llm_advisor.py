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
from baeloop.models import AdvisorAnalysis, AdvisorProposal, ComparisonReport, Intervention
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


PROBE_FIRST_ROOT_CAUSES = {
    "coordinate_click_miss",
    "missed_scroll_target",
}
TERMINAL_ROOT_CAUSES = {
    "terminal_input_action_mismatch",
    "terminal_output_blindness",
}
PATCH_BEARING_KINDS = {"config_patch", "retry_policy", "action_policy", "observation_policy"}


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


def propose_patch_with_llm_v2(
    report: ComparisonReport,
    config: LLMAdvisorConfig | None = None,
    client: ChatClient | None = None,
) -> AdvisorProposal:
    """LLM advisor with deterministic reference and evidence-maturity selection.

    The LLM stages provide analysis and a candidate hypothesis. A deterministic
    selector then chooses between the LLM candidate, the deterministic reference,
    and an investigation fallback based on whether the evidence is mature enough
    for a patch-bearing intervention.
    """
    resolved_config = config or LLMAdvisorConfig()
    resolved_client = client or OpenAICompatibleChatClient()
    deterministic = propose_patch(report)
    analysis = analyze_report(report)
    reference_intervention = deterministic.intervention or propose_intervention(analysis)
    compact_report = _compact_report(report)

    try:
        analyst = _run_analyst(resolved_client, resolved_config, compact_report)
        llm_intervention = _run_hypothesis(
            resolved_client,
            resolved_config,
            compact_report=compact_report,
            analyst=analyst,
            deterministic_intervention=reference_intervention,
        )
        selected, selector_notes = _select_v2_intervention(
            analysis=analysis,
            compact_report=compact_report,
            deterministic_intervention=reference_intervention,
            llm_intervention=llm_intervention,
        )
        _validate_bounded_patch(selected)
        proposal = critique_intervention(analysis, selected)
        critic = _run_critic(
            resolved_client,
            resolved_config,
            compact_report=compact_report,
            analyst=analyst,
            proposal=proposal,
        )
        proposal.critic_notes.extend(
            f"llm critic advisory ({critic.decision}): {note}" for note in critic.notes
        )
        proposal.critic_notes.append("v2 final selector accepted evidence-mature intervention")
        proposal.advisor_mode = "llm-v2"
        proposal.advisor_stage_notes = {
            "analyst": analyst.model_dump(mode="json"),
            "deterministic_reference": reference_intervention.model_dump(mode="json"),
            "llm_candidate": llm_intervention.model_dump(mode="json"),
            "selector": selector_notes,
            "critic": critic.model_dump(mode="json"),
        }
        return proposal
    except Exception as exc:
        try:
            selected, selector_notes = _select_v2_intervention(
                analysis=analysis,
                compact_report=compact_report,
                deterministic_intervention=reference_intervention,
                llm_intervention=reference_intervention,
            )
            _validate_bounded_patch(selected)
            proposal = critique_intervention(analysis, selected)
            proposal.advisor_mode = "llm-v2-fallback"
            proposal.critic_notes.append(f"llm-v2 local fallback: {type(exc).__name__}")
            proposal.advisor_stage_notes = {
                "fallback_error": str(exc),
                "deterministic_reference": reference_intervention.model_dump(mode="json"),
                "selector": selector_notes,
            }
            return proposal
        except Exception as fallback_exc:
            deterministic.advisor_mode = "llm-v2-fallback"
            deterministic.critic_notes.append(
                f"llm-v2 advisor fallback: {type(fallback_exc).__name__}"
            )
            deterministic.advisor_stage_notes = {"fallback_error": str(fallback_exc)}
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
    if intervention.kind in PATCH_BEARING_KINDS:
        if not intervention.patch:
            raise LLMAdvisorError("Patch-bearing LLM intervention omitted patch")


def _select_v2_intervention(
    *,
    analysis: AdvisorAnalysis,
    compact_report: dict[str, Any],
    deterministic_intervention: Intervention,
    llm_intervention: Intervention,
) -> tuple[Intervention, dict[str, Any]]:
    candidate_roots = sorted(analysis.candidate_root_causes)
    selector_notes: list[str] = []

    if deterministic_intervention.id == "hyp_probe_coordinate_control":
        selector_notes.append("control-surface failures require probe before patching")
        return deterministic_intervention, _selector_payload(
            "deterministic_reference", selector_notes
        )

    if deterministic_intervention.id in {
        "hyp_keep_quality_winner",
        "hyp_keep_efficiency_winner",
        "hyp_hold_config_expand_taskset",
        "hyp_combine_scroll_and_terminal_policies",
        "hyp_terminal_keyboard_type",
    }:
        selector_notes.append("deterministic reference is already evidence-mature")
        return deterministic_intervention, _selector_payload(
            "deterministic_reference", selector_notes
        )

    if deterministic_intervention.id == "hyp_extend_step_budget":
        roots = _candidate_roots_for_failure(
            compact_report,
            failure_type="max_steps",
            excluded_roots=TERMINAL_ROOT_CAUSES,
        )
        selector_notes.append("first non-terminal max-step budget hypothesis is patch-mature")
        return _with_evidence_targets(
            deterministic_intervention,
            roots or candidate_roots,
            "evidence_maturity=non_terminal_max_steps",
        ), _selector_payload("deterministic_reference", selector_notes)

    if _needs_probe_before_patch(deterministic_intervention, llm_intervention):
        roots = _probe_first_roots(candidate_roots) or candidate_roots
        selector_notes.append("patch-bearing action policy lacks probe-backed maturity")
        return _investigate_before_patch(roots), _selector_payload(
            "investigation_fallback", selector_notes
        )

    if llm_intervention.kind in {"investigation", "hold"}:
        selector_notes.append("LLM selected conservative non-patch intervention")
        return llm_intervention, _selector_payload("llm_candidate", selector_notes)

    selector_notes.append("falling back to deterministic reference")
    return deterministic_intervention, _selector_payload(
        "deterministic_reference", selector_notes
    )


def _needs_probe_before_patch(
    deterministic_intervention: Intervention,
    llm_intervention: Intervention,
) -> bool:
    candidates = [deterministic_intervention, llm_intervention]
    return any(
        intervention.kind in PATCH_BEARING_KINDS
        and bool(set(intervention.target_root_causes) & PROBE_FIRST_ROOT_CAUSES)
        for intervention in candidates
    )


def _probe_first_roots(candidate_roots: list[str]) -> list[str]:
    return sorted(root for root in candidate_roots if root in PROBE_FIRST_ROOT_CAUSES)


def _investigate_before_patch(roots: list[str]) -> Intervention:
    root_text = ", ".join(roots) if roots else "unclassified candidate failures"
    return Intervention(
        id="hyp_probe_before_action_policy",
        kind="investigation",
        summary="Probe the action surface before adding another action-policy patch.",
        rationale=(
            "Failure evidence points to action-surface root causes, but the report does "
            "not yet prove that a bounded rewrite primitive will solve them."
        ),
        expected_effect=(
            "Collect trace or environment evidence before deciding whether the next "
            "candidate should be a patch-bearing action policy."
        ),
        risk="Does not immediately improve success rate, but avoids overfitting a patch to weak evidence.",
        target_root_causes=roots,
        supported_by=[f"evidence_maturity=needs_probe", f"root_causes={root_text}"],
    )


def _with_evidence_targets(
    intervention: Intervention,
    roots: list[str],
    support: str,
) -> Intervention:
    target_roots = sorted(set(intervention.target_root_causes) | set(roots))
    supported_by = list(intervention.supported_by)
    if support not in supported_by:
        supported_by.append(support)
    return intervention.model_copy(
        update={
            "target_root_causes": target_roots,
            "supported_by": supported_by,
        }
    )


def _candidate_roots_for_failure(
    compact_report: dict[str, Any],
    *,
    failure_type: str,
    excluded_roots: set[str],
) -> list[str]:
    roots = []
    for item in compact_report.get("failure_evidence", {}).get("candidate", []):
        if item.get("failure_type") != failure_type:
            continue
        root = item.get("root_cause")
        if root and root not in excluded_roots:
            roots.append(root)
    return sorted(set(roots))


def _selector_payload(selected_source: str, notes: list[str]) -> dict[str, Any]:
    return {
        "selected_source": selected_source,
        "notes": notes,
    }


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
