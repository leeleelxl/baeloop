from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from baeloop.advisor import propose_patch
from baeloop.io import read_model_json
from baeloop.llm_advisor import LLMAdvisorConfig, propose_patch_with_llm, propose_patch_with_llm_v2
from baeloop.models import AdvisorProposal, ComparisonReport
from baeloop.patcher import ALLOWED_PATCH_KEYS
from baeloop.tool_agent import run_tool_optimization_agent


@dataclass(frozen=True)
class AdvisorEvalCase:
    id: str
    report_path: Path
    expected_direction: str
    expected_root_causes: tuple[str, ...] = ()


DEFAULT_EVAL_CASES = [
    AdvisorEvalCase(
        id="hard_retry_no_gain",
        report_path=Path("reports/agentlab_hard_compare.json"),
        expected_direction="extend_step_budget",
        expected_root_causes=("autocomplete_validation_loop",),
    ),
    AdvisorEvalCase(
        id="hard_budget_needs_evidence",
        report_path=Path("reports/agentlab_hard_budget30_compare.json"),
        expected_direction="investigate",
        expected_root_causes=("coordinate_click_miss", "missed_scroll_target"),
    ),
    AdvisorEvalCase(
        id="hard_scroll_to_terminal",
        report_path=Path("reports/agentlab_hard_scroll_policy_compare.json"),
        expected_direction="terminal_policy",
        expected_root_causes=("terminal_input_action_mismatch",),
    ),
    AdvisorEvalCase(
        id="hard_terminal_regresses_scroll",
        report_path=Path("reports/agentlab_hard_terminal_policy_compare.json"),
        expected_direction="compose_policies",
        expected_root_causes=("missed_scroll_target", "terminal_input_action_mismatch"),
    ),
    AdvisorEvalCase(
        id="hard_combined_remaining_coordinate",
        report_path=Path("reports/agentlab_hard_combined_policy_compare.json"),
        expected_direction="investigate",
        expected_root_causes=("coordinate_click_miss",),
    ),
    AdvisorEvalCase(
        id="hard_full_quality_winner",
        report_path=Path("reports/agentlab_hard_full_policy_compare.json"),
        expected_direction="quality_winner",
    ),
    AdvisorEvalCase(
        id="broad_full_quality_winner",
        report_path=Path("reports/agentlab_broad_full_policy_compare.json"),
        expected_direction="quality_winner",
    ),
    AdvisorEvalCase(
        id="control_boundary",
        report_path=Path("reports/agentlab_control_full_policy_compare.json"),
        expected_direction="probe_coordinate_control",
        expected_root_causes=(
            "coordinate_click_surface_mismatch",
            "coordinate_drag_surface_mismatch",
            "coordinate_draw_surface_mismatch",
            "directional_drag_control_mismatch",
            "list_drag_semantics_mismatch",
        ),
    ),
]

HOLDOUT_EVAL_CASES = [
    AdvisorEvalCase(
        id="holdout_core_saturated",
        report_path=Path("reports/agentlab_core_compare.json"),
        expected_direction="hold_expand_taskset",
    ),
    AdvisorEvalCase(
        id="holdout_challenge_efficiency_winner",
        report_path=Path("reports/agentlab_challenge_compare.json"),
        expected_direction="efficiency_winner",
    ),
    AdvisorEvalCase(
        id="holdout_hard_repeat_efficiency_winner",
        report_path=Path("reports/agentlab_hard_full_policy_repeat_compare.json"),
        expected_direction="efficiency_winner",
    ),
    AdvisorEvalCase(
        id="holdout_combined_vs_terminal_remaining_coordinate",
        report_path=Path("reports/agentlab_hard_combined_vs_terminal_policy_compare.json"),
        expected_direction="investigate",
        expected_root_causes=("coordinate_click_miss",),
    ),
    AdvisorEvalCase(
        id="holdout_mock_timeout_budget",
        report_path=Path("reports/mock_compare.json"),
        expected_direction="extend_step_budget",
    ),
    AdvisorEvalCase(
        id="holdout_agentlab_smoke_saturated",
        report_path=Path("reports/agentlab_smoke_compare.json"),
        expected_direction="hold_expand_taskset",
    ),
    AdvisorEvalCase(
        id="holdout_mock_advisor_quality_winner",
        report_path=Path("reports/mock_advisor_compare.json"),
        expected_direction="quality_winner",
    ),
    AdvisorEvalCase(
        id="holdout_sample_retry_invalid_or_noop",
        report_path=Path("reports/sample_compare.json"),
        expected_direction="retry_invalid_or_noop",
    ),
    AdvisorEvalCase(
        id="holdout_budget30_to_combined_remaining_coordinate",
        report_path=Path("reports/agentlab_hard_budget30_vs_combined_policy_compare.json"),
        expected_direction="investigate",
        expected_root_causes=("coordinate_click_miss",),
    ),
    AdvisorEvalCase(
        id="holdout_hard_retry_to_full_quality_winner",
        report_path=Path("reports/agentlab_hard_retry_vs_full_policy_compare.json"),
        expected_direction="quality_winner",
    ),
]

TOOL_EVAL_CASES = [
    AdvisorEvalCase(
        id="tool_terminal_probe_to_policy",
        report_path=Path("reports/agentlab_hard_scroll_policy_compare.json"),
        expected_direction="terminal_policy",
        expected_root_causes=("terminal_input_action_mismatch",),
    ),
    AdvisorEvalCase(
        id="tool_compose_scroll_terminal",
        report_path=Path("reports/agentlab_hard_terminal_policy_compare.json"),
        expected_direction="compose_policies",
        expected_root_causes=("missed_scroll_target", "terminal_input_action_mismatch"),
    ),
    AdvisorEvalCase(
        id="tool_grid_probe_to_policy",
        report_path=Path("reports/agentlab_hard_combined_vs_terminal_policy_compare.json"),
        expected_direction="grid_policy",
        expected_root_causes=("coordinate_click_miss",),
    ),
    AdvisorEvalCase(
        id="tool_control_boundary_probe",
        report_path=Path("reports/agentlab_control_full_policy_compare.json"),
        expected_direction="probe_coordinate_control",
        expected_root_causes=(
            "coordinate_click_surface_mismatch",
            "coordinate_drag_surface_mismatch",
            "coordinate_draw_surface_mismatch",
            "directional_drag_control_mismatch",
            "list_drag_semantics_mismatch",
        ),
    ),
    AdvisorEvalCase(
        id="tool_broad_quality_hold",
        report_path=Path("reports/agentlab_broad_full_policy_compare.json"),
        expected_direction="quality_winner",
    ),
]

EVAL_CASE_SUITES = {
    "default": DEFAULT_EVAL_CASES,
    "holdout": HOLDOUT_EVAL_CASES,
    "tool": TOOL_EVAL_CASES,
}


def get_advisor_eval_cases(case_suite: str) -> list[AdvisorEvalCase]:
    try:
        return EVAL_CASE_SUITES[case_suite]
    except KeyError as exc:
        allowed = ", ".join(sorted(EVAL_CASE_SUITES))
        raise ValueError(f"Unknown advisor eval case suite `{case_suite}`. Use one of: {allowed}") from exc


def run_advisor_eval(
    *,
    cases: list[AdvisorEvalCase] | None = None,
    case_suite: str = "default",
    include_llm: bool = False,
    include_llm_v2: bool = False,
    include_tool_agent: bool = False,
    include_tool_pretool: bool = False,
    reports_dir: Path = Path("reports"),
    llm_config: LLMAdvisorConfig | None = None,
) -> dict:
    resolved_cases = cases if cases is not None else get_advisor_eval_cases(case_suite)
    resolved_suite = "custom" if cases is not None else case_suite
    rows: list[dict] = []
    for case in resolved_cases:
        report = read_model_json(case.report_path, ComparisonReport)
        rows.append(_score_case(case, "deterministic", propose_patch(report)))
        if include_llm:
            rows.append(
                _score_case(
                    case,
                    "llm",
                    propose_patch_with_llm(report, config=llm_config),
                )
            )
        if include_llm_v2:
            rows.append(
                _score_case(
                    case,
                    "llm-v2",
                    propose_patch_with_llm_v2(report, config=llm_config),
                )
            )
        if include_tool_agent or include_tool_pretool:
            tool_run = run_tool_optimization_agent(case.report_path, reports_dir=reports_dir)
            if include_tool_pretool:
                rows.append(
                    _score_case(
                        case,
                        "tool-agent-pretool",
                        tool_run.pre_tool_proposal,
                    )
                )
            if include_tool_agent:
                rows.append(_score_case(case, "tool-agent", tool_run.proposal))

    return {
        "case_suite": resolved_suite,
        "case_count": len(resolved_cases),
        "include_llm": include_llm,
        "include_llm_v2": include_llm_v2,
        "include_tool_agent": include_tool_agent,
        "include_tool_pretool": include_tool_pretool,
        "summary": _summarize(rows),
        "rows": rows,
    }


def render_advisor_eval_markdown(report: dict) -> str:
    lines = [
        "# Advisor Evaluation",
        "",
        f"- Case suite: `{report.get('case_suite', 'default')}`",
        f"- Cases: `{report['case_count']}`",
        f"- Include LLM: `{report['include_llm']}`",
        f"- Include LLM v2: `{report.get('include_llm_v2', False)}`",
        f"- Include Tool Agent: `{report.get('include_tool_agent', False)}`",
        f"- Include Tool Pretool: `{report.get('include_tool_pretool', False)}`",
        "",
        "## Summary",
        "",
        "| Advisor | Rows | Avg Score | Direction Match | Safe Patch | Evidence Use | Boundary Awareness |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for advisor, item in sorted(report["summary"].items()):
        lines.append(
            f"| `{advisor}` | {item['rows']} | {item['avg_score']:.3f} | "
            f"{item['direction_match_rate']:.3f} | {item['safe_patch_rate']:.3f} | "
            f"{item['evidence_use_rate']:.3f} | {item['boundary_awareness_rate']:.3f} |"
        )

    lines.extend(
        [
            "",
            "## Cases",
            "",
            "| Case | Advisor | Mode | Source | Hypothesis | Score | Direction | Safe Patch | Evidence | Boundary | Notes |",
            "|---|---|---|---|---|---:|---:|---:|---:|---:|---|",
        ]
    )
    for row in report["rows"]:
        notes = "<br>".join(_escape_markdown_cell(note) for note in row["notes"][:4])
        lines.append(
            f"| `{row['case_id']}` | `{row['advisor']}` | `{row['proposal_mode']}` | "
            f"`{row.get('selected_source', '-')}` | `{row['hypothesis_id']}` | "
            f"{row['score']:.3f} | {_mark(row['direction_match'])} | "
            f"{_mark(row['safe_patch'])} | {_mark(row['uses_failure_evidence'])} | "
            f"{_mark(row['boundary_awareness'])} | {notes} |"
        )

    return "\n".join(lines) + "\n"


def _score_case(
    case: AdvisorEvalCase,
    advisor: str,
    proposal: AdvisorProposal,
) -> dict:
    safe_patch = _safe_patch(proposal)
    direction_match = _direction_matches(case.expected_direction, proposal)
    uses_failure_evidence = _uses_failure_evidence(case.expected_root_causes, proposal)
    boundary_awareness = _boundary_awareness(case.expected_direction, proposal)
    critic_ok = proposal.critic_decision == "accepted"
    schema_valid = bool(proposal.hypothesis_id and proposal.summary and proposal.rationale)

    components = {
        "schema_valid": schema_valid,
        "critic_ok": critic_ok,
        "safe_patch": safe_patch,
        "direction_match": direction_match,
        "uses_failure_evidence": uses_failure_evidence,
        "boundary_awareness": boundary_awareness,
    }
    score = sum(1 for value in components.values() if value) / len(components)
    notes = _notes(case, proposal, components)
    selected_source = _selected_source(proposal)
    return {
        "case_id": case.id,
        "advisor": advisor,
        "proposal_mode": proposal.advisor_mode,
        "selected_source": selected_source,
        "used_fallback": proposal.advisor_mode.endswith("fallback")
        or "fallback_error" in proposal.advisor_stage_notes,
        "hypothesis_id": proposal.hypothesis_id,
        "critic_decision": proposal.critic_decision,
        "expected_direction": case.expected_direction,
        "score": score,
        **components,
        "patch_keys": sorted(proposal.patch),
        "target_root_causes": (
            proposal.intervention.target_root_causes if proposal.intervention else []
        ),
        "notes": notes,
        "proposal": proposal.model_dump(mode="json"),
    }


def _summarize(rows: list[dict]) -> dict[str, dict]:
    grouped: dict[str, list[dict]] = {}
    for row in rows:
        grouped.setdefault(row["advisor"], []).append(row)
    summary: dict[str, dict] = {}
    for advisor, items in grouped.items():
        summary[advisor] = {
            "rows": len(items),
            "avg_score": _avg(items, "score"),
            "direction_match_rate": _avg_bool(items, "direction_match"),
            "safe_patch_rate": _avg_bool(items, "safe_patch"),
            "evidence_use_rate": _avg_bool(items, "uses_failure_evidence"),
            "boundary_awareness_rate": _avg_bool(items, "boundary_awareness"),
        }
    return summary


def _avg(items: list[dict], key: str) -> float:
    return sum(float(item[key]) for item in items) / len(items)


def _avg_bool(items: list[dict], key: str) -> float:
    return sum(1 for item in items if item[key]) / len(items)


def _safe_patch(proposal: AdvisorProposal) -> bool:
    if proposal.patch and set(proposal.patch) - ALLOWED_PATCH_KEYS:
        return False
    patch_bearing = {"config_patch", "retry_policy", "action_policy", "observation_policy"}
    if proposal.intervention and proposal.intervention.kind in patch_bearing:
        return bool(proposal.patch)
    return proposal.patch == {}


def _direction_matches(expected_direction: str, proposal: AdvisorProposal) -> bool:
    predicates: dict[str, Callable[[AdvisorProposal], bool]] = {
        "extend_step_budget": lambda item: item.hypothesis_id == "hyp_extend_step_budget",
        "investigate": lambda item: (
            item.intervention is not None and item.intervention.kind in {"investigation", "hold"}
        ),
        "terminal_policy": lambda item: item.hypothesis_id == "hyp_terminal_keyboard_type",
        "compose_policies": lambda item: item.hypothesis_id
        == "hyp_combine_scroll_and_terminal_policies",
        "quality_winner": lambda item: item.hypothesis_id == "hyp_keep_quality_winner",
        "efficiency_winner": lambda item: item.hypothesis_id == "hyp_keep_efficiency_winner",
        "hold_expand_taskset": lambda item: item.hypothesis_id
        == "hyp_hold_config_expand_taskset",
        "probe_coordinate_control": lambda item: item.hypothesis_id
        == "hyp_probe_coordinate_control",
        "retry_invalid_or_noop": lambda item: item.hypothesis_id
        == "hyp_retry_invalid_or_noop",
        "grid_policy": lambda item: item.hypothesis_id == "hyp_grid_coordinate_click",
    }
    return predicates[expected_direction](proposal)


def _uses_failure_evidence(
    expected_root_causes: tuple[str, ...],
    proposal: AdvisorProposal,
) -> bool:
    if not expected_root_causes:
        return True
    if not proposal.intervention:
        return False
    targets = set(proposal.intervention.target_root_causes)
    support = " ".join(proposal.intervention.supported_by)
    return any(root in targets or root in support for root in expected_root_causes)


def _boundary_awareness(expected_direction: str, proposal: AdvisorProposal) -> bool:
    if expected_direction == "probe_coordinate_control":
        text = " ".join(
            [
                proposal.summary,
                proposal.rationale,
                proposal.expected_effect,
                " ".join(proposal.critic_notes),
            ]
        ).lower()
        return not proposal.patch and any(
            term in text for term in ("coordinate", "probe", "boundary", "capability")
        )
    if expected_direction == "investigate":
        return not proposal.patch
    return True


def _notes(case: AdvisorEvalCase, proposal: AdvisorProposal, components: dict[str, bool]) -> list[str]:
    notes = [
        f"expected={case.expected_direction}",
        f"mode={proposal.advisor_mode}",
    ]
    for key, passed in components.items():
        if not passed:
            notes.append(f"failed_{key}")
    if proposal.critic_notes:
        notes.append(proposal.critic_notes[-1])
    return notes


def _selected_source(proposal: AdvisorProposal) -> str:
    selector = proposal.advisor_stage_notes.get("selector")
    if isinstance(selector, dict) and selector.get("selected_source"):
        return str(selector["selected_source"])
    if proposal.advisor_mode.endswith("fallback"):
        return "fallback"
    tool_agent = proposal.advisor_stage_notes.get("tool_agent")
    if isinstance(tool_agent, dict):
        if tool_agent.get("selected_source"):
            return str(tool_agent["selected_source"])
        if proposal.advisor_mode == "tool-agent-pretool":
            return "pretool"
        return "tool_agent"
    return "-"


def _mark(value: bool) -> str:
    return "yes" if value else "no"


def _escape_markdown_cell(value: str) -> str:
    return value.replace("|", "\\|")
