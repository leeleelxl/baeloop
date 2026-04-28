from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from baeloop.advisor_analysis import analyze_report
from baeloop.advisor_critic import critique_intervention
from baeloop.io import read_json_dict, read_model_json
from baeloop.models import AdvisorProposal, ComparisonReport, Intervention


class ToolCallRecord(BaseModel):
    tool_name: str
    args: dict[str, Any] = Field(default_factory=dict)
    observation: dict[str, Any] = Field(default_factory=dict)


class ToolAgentRun(BaseModel):
    report_path: str
    pre_tool_hypothesis_id: str
    final_hypothesis_id: str
    decision_changed_by_tools: bool
    selected_root_cause: str | None = None
    tool_calls: list[ToolCallRecord]
    pre_tool_proposal: AdvisorProposal
    proposal: AdvisorProposal


def run_tool_optimization_agent(
    report_path: Path,
    *,
    reports_dir: Path = Path("reports"),
) -> ToolAgentRun:
    """Run a bounded tool-using optimization advisor over one compare report.

    This is an upper-layer optimization agent loop. It reads existing local
    artifacts instead of rerunning the browser or calling an LLM.
    """
    report, inspect_call = _inspect_compare_report(report_path)
    analysis = analyze_report(report)
    candidate_roots = _candidate_root_causes(report)
    baseline_roots = _baseline_root_causes(report)
    pre_tool = _investigate_before_tools(candidate_roots)
    pre_tool_proposal = critique_intervention(analysis, pre_tool)
    pre_tool_proposal.advisor_mode = "tool-agent-pretool"
    pre_tool_proposal.advisor_stage_notes["tool_agent"] = {
        "selected_source": "pretool_investigation",
        "tool_call_count": 0,
        "tool_names": [],
        "decision_changed_by_tools": False,
    }

    tool_calls = [inspect_call]
    tool_observations: dict[str, dict[str, Any]] = {}
    for root_cause in _tool_relevant_roots(
        candidate_roots,
        baseline_roots,
        regression_count=report.regression_count,
    ):
        if root_cause == "terminal_input_action_mismatch":
            call = _inspect_terminal_probe(reports_dir)
        elif root_cause == "missed_scroll_target":
            call = _inspect_scroll_replay(reports_dir)
        elif root_cause == "coordinate_click_miss":
            call = _inspect_grid_probe(reports_dir)
        else:
            continue
        tool_calls.append(call)
        tool_observations[root_cause] = call.observation

    selected_root = _select_root_cause(
        tool_observations,
        regression_count=report.regression_count,
        candidate_roots=candidate_roots,
        baseline_roots=baseline_roots,
    )
    intervention = _intervention_from_tool_evidence(selected_root, tool_observations)
    if intervention is None:
        intervention = pre_tool

    proposal = critique_intervention(analysis, intervention)
    proposal.advisor_mode = "tool-agent"
    proposal.advisor_stage_notes["tool_agent"] = {
        "pre_tool_hypothesis_id": pre_tool.id,
        "selected_root_cause": selected_root,
        "tool_call_count": len(tool_calls),
        "tool_names": [call.tool_name for call in tool_calls],
        "decision_changed_by_tools": intervention.id != pre_tool.id,
    }

    return ToolAgentRun(
        report_path=str(report_path),
        pre_tool_hypothesis_id=pre_tool.id,
        final_hypothesis_id=proposal.hypothesis_id,
        decision_changed_by_tools=proposal.hypothesis_id != pre_tool.id,
        selected_root_cause=selected_root,
        tool_calls=tool_calls,
        pre_tool_proposal=pre_tool_proposal,
        proposal=proposal,
    )


def render_tool_agent_markdown(run: ToolAgentRun) -> str:
    lines = [
        "# Tool-Using Optimization Agent Run",
        "",
        f"- Report: `{run.report_path}`",
        f"- Pre-tool hypothesis: `{run.pre_tool_hypothesis_id}`",
        f"- Final hypothesis: `{run.final_hypothesis_id}`",
        f"- Selected root cause: `{run.selected_root_cause or '-'}`",
        f"- Decision changed by tools: `{str(run.decision_changed_by_tools).lower()}`",
        "",
        "## Tool Calls",
        "",
        "| # | Tool | Observation |",
        "|---:|---|---|",
    ]
    for index, call in enumerate(run.tool_calls, start=1):
        lines.append(
            f"| {index} | `{call.tool_name}` | {_format_observation(call.observation)} |"
        )

    lines.extend(
        [
            "",
            "## Final Proposal",
            "",
            f"- Hypothesis: `{run.proposal.hypothesis_id}`",
            f"- Summary: {run.proposal.summary}",
            f"- Critic decision: `{run.proposal.critic_decision}`",
            "",
            "```json",
            json.dumps(run.proposal.patch, indent=2, sort_keys=True),
            "```",
        ]
    )
    return "\n".join(lines) + "\n"


def _inspect_compare_report(report_path: Path) -> tuple[ComparisonReport, ToolCallRecord]:
    report = read_model_json(report_path, ComparisonReport)
    candidate_roots = _candidate_root_causes(report)
    baseline_roots = _baseline_root_causes(report)
    observation = {
        "baseline_config_id": report.baseline_config_id,
        "candidate_config_id": report.candidate_config_id,
        "success_rate_delta": report.metrics["delta"]["success_rate"],
        "regression_count": report.regression_count,
        "improvement_count": len(report.improvements),
        "baseline_root_causes": baseline_roots,
        "candidate_root_causes": candidate_roots,
    }
    return report, ToolCallRecord(
        tool_name="inspect_compare_report",
        args={"report_path": str(report_path)},
        observation=observation,
    )


def _inspect_terminal_probe(reports_dir: Path) -> ToolCallRecord:
    path = reports_dir / "agentlab_terminal_action_probe.json"
    payload = read_json_dict(path)
    results = payload.get("results", [])
    fill_result = next((item for item in results if item.get("name") == "fill_press"), {})
    keyboard_visible = [
        item.get("name")
        for item in results
        if item.get("command_visible") and "keyboard_type" in " ".join(item.get("actions", []))
    ]
    oracle = payload.get("oracle_result") or {}
    observation = {
        "artifact": str(path),
        "fill_command_visible": bool(fill_result.get("command_visible")),
        "keyboard_visible_sequences": keyboard_visible,
        "oracle_reward": float(oracle.get("reward", 0.0)),
        "patch_mature": (not fill_result.get("command_visible", True))
        and bool(keyboard_visible)
        and float(oracle.get("reward", 0.0)) >= 1.0,
    }
    return ToolCallRecord(
        tool_name="inspect_terminal_probe",
        args={"artifact": str(path)},
        observation=observation,
    )


def _inspect_scroll_replay(reports_dir: Path) -> ToolCallRecord:
    path = reports_dir / "agentlab_social_scroll_policy_replay.json"
    payload = read_json_dict(path)
    first = payload.get("first_intervention") or {}
    observation = {
        "artifact": str(path),
        "policy_name": payload.get("policy_name"),
        "fired": bool(payload.get("fired")),
        "applied_count": int(payload.get("applied_count", 0)),
        "first_step": first.get("step"),
        "rewritten_action": first.get("rewritten_action"),
        "patch_mature": bool(payload.get("fired")) and int(payload.get("applied_count", 0)) > 0,
    }
    return ToolCallRecord(
        tool_name="inspect_policy_replay",
        args={"artifact": str(path)},
        observation=observation,
    )


def _inspect_grid_probe(reports_dir: Path) -> ToolCallRecord:
    path = reports_dir / "agentlab_grid_coordinate_probe.json"
    payload = read_json_dict(path)
    results = payload.get("results", [])
    svg_root = next((item for item in results if item.get("name") == "svg_root_bid_click"), {})
    mapped = next((item for item in results if item.get("name") == "mapped_mouse_click"), {})
    final_state = mapped.get("final_state") or {}
    observation = {
        "artifact": str(path),
        "svg_root_reward": float(svg_root.get("reward", 0.0)),
        "mapped_mouse_click_reward": float(mapped.get("reward", 0.0)),
        "target_coordinate": final_state.get("target_coordinate"),
        "target_click_point": final_state.get("target_click_point"),
        "patch_mature": float(mapped.get("reward", 0.0)) >= 1.0
        and float(svg_root.get("reward", 0.0)) < 1.0,
    }
    return ToolCallRecord(
        tool_name="inspect_grid_probe",
        args={"artifact": str(path)},
        observation=observation,
    )


def _candidate_root_causes(report: ComparisonReport) -> list[str]:
    return sorted({item.root_cause for item in report.failure_evidence.get("candidate", [])})


def _baseline_root_causes(report: ComparisonReport) -> list[str]:
    return sorted({item.root_cause for item in report.failure_evidence.get("baseline", [])})


def _tool_relevant_roots(
    candidate_roots: list[str],
    baseline_roots: list[str],
    *,
    regression_count: int,
) -> list[str]:
    priority = [
        "terminal_input_action_mismatch",
        "missed_scroll_target",
        "coordinate_click_miss",
    ]
    roots = set(candidate_roots)
    if (
        regression_count > 0
        and "missed_scroll_target" in candidate_roots
        and "terminal_input_action_mismatch" in baseline_roots
    ):
        roots.add("terminal_input_action_mismatch")
    return [root for root in priority if root in roots]


def _select_root_cause(
    tool_observations: dict[str, dict[str, Any]],
    *,
    regression_count: int,
    candidate_roots: list[str],
    baseline_roots: list[str],
) -> str | None:
    if (
        regression_count > 0
        and "missed_scroll_target" in candidate_roots
        and "terminal_input_action_mismatch" in baseline_roots
        and tool_observations.get("missed_scroll_target", {}).get("patch_mature")
        and tool_observations.get("terminal_input_action_mismatch", {}).get("patch_mature")
    ):
        return "compose_scroll_and_terminal"

    for root in [
        "terminal_input_action_mismatch",
        "missed_scroll_target",
        "coordinate_click_miss",
    ]:
        if tool_observations.get(root, {}).get("patch_mature"):
            return root
    return None


def _intervention_from_tool_evidence(
    selected_root: str | None,
    tool_observations: dict[str, dict[str, Any]],
) -> Intervention | None:
    if selected_root == "terminal_input_action_mismatch":
        return _terminal_keyboard_intervention(tool_observations[selected_root])
    if selected_root == "missed_scroll_target":
        return _scroll_before_submit_intervention(tool_observations[selected_root])
    if selected_root == "coordinate_click_miss":
        return _grid_coordinate_intervention(tool_observations[selected_root])
    if selected_root == "compose_scroll_and_terminal":
        return _compose_scroll_terminal_intervention(tool_observations)
    return None


def _investigate_before_tools(root_causes: list[str]) -> Intervention:
    root_text = ", ".join(root_causes) if root_causes else "no candidate root causes"
    return Intervention(
        id="hyp_tool_investigate_before_patch",
        kind="investigation",
        summary="Use diagnostic tools before emitting the next optimization patch.",
        rationale=(
            "The compare report points to actionable root causes, but the optimization "
            "agent should first inspect probe or replay evidence before changing config."
        ),
        expected_effect="Avoid unsupported patches while collecting tool observations.",
        risk="Adds an intermediate diagnostic step before success rate can improve.",
        target_root_causes=root_causes,
        supported_by=[f"candidate_root_causes={root_text}"],
    )


def _terminal_keyboard_intervention(observation: dict[str, Any]) -> Intervention:
    return Intervention(
        id="hyp_terminal_keyboard_type",
        kind="action_policy",
        summary="Enable a terminal keyboard-type action policy after probe-backed evidence.",
        rationale="The terminal probe shows fill/press does not make commands visible, while keyboard typing does.",
        expected_effect="Let terminal commands reach MiniWoB's custom terminal input surface.",
        risk="Fixes input delivery only; incorrect command planning can still fail.",
        patch={
            "action_policy": {
                "enabled": True,
                "name": "terminal_keyboard_type",
                "max_interventions": 20,
            }
        },
        target_root_causes=["terminal_input_action_mismatch"],
        supported_by=[
            "root_cause=terminal_input_action_mismatch",
            f"tool=inspect_terminal_probe artifact={observation.get('artifact')}",
            f"oracle_reward={observation.get('oracle_reward')}",
        ],
    )


def _scroll_before_submit_intervention(observation: dict[str, Any]) -> Intervention:
    return Intervention(
        id="hyp_scroll_before_submit",
        kind="action_policy",
        summary="Enable a bounded scroll-before-submit policy after replay evidence.",
        rationale="The replay tool shows the scroll policy fires on the historical hidden-target trace.",
        expected_effect="Reveal hidden remaining targets before submitting social-media tasks.",
        risk="May add one extra scroll on matching tasks if the hidden-target heuristic is too broad.",
        patch={
            "action_policy": {
                "enabled": True,
                "name": "scroll_before_submit",
                "max_interventions": 1,
                "scroll_delta_y": 621,
            }
        },
        target_root_causes=["missed_scroll_target"],
        supported_by=[
            "root_cause=missed_scroll_target",
            f"tool=inspect_policy_replay artifact={observation.get('artifact')}",
            f"applied_count={observation.get('applied_count')}",
        ],
    )


def _grid_coordinate_intervention(observation: dict[str, Any]) -> Intervention:
    return Intervention(
        id="hyp_grid_coordinate_click",
        kind="action_policy",
        summary="Enable a coordinate-aware click policy after grid probe evidence.",
        rationale="The grid probe shows SVG-root bid click fails while mapped mouse_click solves the target.",
        expected_effect="Convert SVG-root grid clicks into precise mouse clicks when target geometry is available.",
        risk="Should only fire when coordinate and SVG geometry are confidently parsed.",
        patch={
            "action_policy": {
                "enabled": True,
                "name": "composite",
                "policies": [
                    "scroll_before_submit",
                    "terminal_keyboard_type",
                    "grid_coordinate_click",
                ],
                "max_interventions": 25,
                "policy_limits": {
                    "scroll_before_submit": 1,
                    "terminal_keyboard_type": 20,
                    "grid_coordinate_click": 1,
                },
                "scroll_delta_y": 621,
            }
        },
        target_root_causes=["coordinate_click_miss"],
        supported_by=[
            "root_cause=coordinate_click_miss",
            f"tool=inspect_grid_probe artifact={observation.get('artifact')}",
            f"mapped_mouse_click_reward={observation.get('mapped_mouse_click_reward')}",
            f"target_click_point={observation.get('target_click_point')}",
        ],
    )


def _compose_scroll_terminal_intervention(
    tool_observations: dict[str, dict[str, Any]]
) -> Intervention:
    scroll_observation = tool_observations["missed_scroll_target"]
    terminal_observation = tool_observations["terminal_input_action_mismatch"]
    return Intervention(
        id="hyp_combine_scroll_and_terminal_policies",
        kind="action_policy",
        summary="Compose scroll and terminal policies after both tools show mature evidence.",
        rationale=(
            "The candidate regressed on hidden social targets while the baseline still had "
            "terminal input mismatch; replay and probe artifacts support preserving both policies."
        ),
        expected_effect="Restore hidden-target scrolling while keeping terminal keyboard input behavior.",
        risk="Combining policies expands wrapper surface area, so each sub-policy stays bounded.",
        patch={
            "action_policy": {
                "enabled": True,
                "name": "composite",
                "policies": [
                    "scroll_before_submit",
                    "terminal_keyboard_type",
                ],
                "max_interventions": 20,
                "policy_limits": {
                    "scroll_before_submit": 1,
                    "terminal_keyboard_type": 20,
                },
                "scroll_delta_y": 621,
            }
        },
        target_root_causes=[
            "missed_scroll_target",
            "terminal_input_action_mismatch",
        ],
        supported_by=[
            "candidate_root_cause=missed_scroll_target",
            "baseline_root_cause=terminal_input_action_mismatch",
            f"tool=inspect_policy_replay artifact={scroll_observation.get('artifact')}",
            f"tool=inspect_terminal_probe artifact={terminal_observation.get('artifact')}",
        ],
    )


def _format_observation(observation: dict[str, Any]) -> str:
    items = []
    for key, value in observation.items():
        if isinstance(value, list):
            rendered = ", ".join(str(item) for item in value)
        else:
            rendered = str(value)
        items.append(f"`{key}`={rendered}")
    return "<br>".join(items)
