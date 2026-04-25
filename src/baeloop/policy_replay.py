from __future__ import annotations

from pathlib import Path
import gzip
import pickle
import re
from typing import Any

from pydantic import BaseModel

from baeloop.action_policy import SCROLL_BEFORE_SUBMIT, ActionPolicyState, apply_action_policy
from baeloop.models import ActionPolicyConfig


class PolicyReplayDecision(BaseModel):
    step: int
    original_action: str | None
    applied: bool
    rewritten_action: str | None = None
    reason: str | None = None


class PolicyReplayReport(BaseModel):
    trace_dir: str
    policy_name: str
    max_interventions: int
    step_count: int
    applied_count: int
    fired: bool
    first_intervention: PolicyReplayDecision | None = None
    decisions: list[PolicyReplayDecision]


def replay_action_policy_trace(trace_dir: Path, policy: ActionPolicyConfig) -> PolicyReplayReport:
    _validate_policy(policy)
    state = ActionPolicyState()
    decisions: list[PolicyReplayDecision] = []

    for step_file in _step_files(trace_dir):
        step_info = _load_step_info(step_file)
        action = getattr(step_info, "action", None)
        obs = getattr(step_info, "obs", None)
        if not isinstance(obs, dict):
            obs = {}

        decision = apply_action_policy(
            action=action,
            obs=obs,
            policy=policy,
            state=state,
        )
        decisions.append(
            PolicyReplayDecision(
                step=_step_index(step_file),
                original_action=action,
                applied=decision.applied,
                rewritten_action=decision.action if decision.applied else None,
                reason=decision.reason if decision.applied else None,
            )
        )

    applied = [decision for decision in decisions if decision.applied]
    return PolicyReplayReport(
        trace_dir=str(trace_dir),
        policy_name=policy.name,
        max_interventions=policy.max_interventions,
        step_count=len(decisions),
        applied_count=len(applied),
        fired=bool(applied),
        first_intervention=applied[0] if applied else None,
        decisions=decisions,
    )


def render_policy_replay_markdown(report: PolicyReplayReport) -> str:
    lines = [
        f"# Policy Replay: {report.policy_name}",
        "",
        f"- Trace: `{report.trace_dir}`",
        f"- Steps replayed: `{report.step_count}`",
        f"- Max interventions: `{report.max_interventions}`",
        f"- Applied interventions: `{report.applied_count}`",
        f"- Fired: `{str(report.fired).lower()}`",
        "",
    ]
    if report.first_intervention:
        first = report.first_intervention
        lines.extend(
            [
                "## First Intervention",
                "",
                f"- Step: `{first.step}`",
                f"- Original action: `{first.original_action}`",
                f"- Rewritten action: `{first.rewritten_action}`",
                f"- Reason: {first.reason}",
                "",
            ]
        )

    lines.extend(
        [
            "## Decisions",
            "",
            "| Step | Applied | Original Action | Rewritten Action |",
            "|---:|---|---|---|",
        ]
    )
    for decision in report.decisions:
        rewritten = decision.rewritten_action or ""
        original = decision.original_action or ""
        lines.append(
            f"| {decision.step} | {str(decision.applied).lower()} | `{original}` | `{rewritten}` |"
        )
    return "\n".join(lines) + "\n"


def _validate_policy(policy: ActionPolicyConfig) -> None:
    if not policy.enabled:
        raise ValueError("Action policy replay requires an enabled action_policy")
    if policy.name != SCROLL_BEFORE_SUBMIT:
        raise ValueError(f"Unsupported action policy `{policy.name}`")
    if policy.max_interventions <= 0:
        raise ValueError("Action policy replay requires max_interventions > 0")


def _step_files(trace_dir: Path) -> list[Path]:
    step_files = [path for path in trace_dir.glob("step_*.pkl.gz") if _is_step_file(path)]
    if not step_files:
        raise ValueError(f"No AgentLab step_*.pkl.gz files found in {trace_dir}")
    return sorted(step_files, key=_step_index)


def _is_step_file(path: Path) -> bool:
    return re.fullmatch(r"step_\d+\.pkl\.gz", path.name) is not None


def _step_index(path: Path) -> int:
    match = re.fullmatch(r"step_(\d+)\.pkl\.gz", path.name)
    if not match:
        raise ValueError(f"Invalid AgentLab step file name: {path.name}")
    return int(match.group(1))


def _load_step_info(path: Path) -> Any:
    try:
        with gzip.open(path, "rb") as handle:
            return pickle.load(handle)
    except Exception as exc:
        raise ValueError(f"Failed to load AgentLab step file {path}") from exc
