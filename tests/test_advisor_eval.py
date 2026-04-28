from __future__ import annotations

from pathlib import Path

from baeloop.advisor_eval import (
    AdvisorEvalCase,
    get_advisor_eval_cases,
    render_advisor_eval_markdown,
    run_advisor_eval,
)
from baeloop.compare import build_comparison_report
from baeloop.io import write_json
from baeloop.models import RunRecord


def test_advisor_eval_scores_direction_and_boundary_awareness(tmp_path: Path) -> None:
    report_path = tmp_path / "control_compare.json"
    write_json(report_path, _control_boundary_report())
    case = AdvisorEvalCase(
        id="control_boundary",
        report_path=report_path,
        expected_direction="probe_coordinate_control",
        expected_root_causes=("coordinate_click_surface_mismatch",),
    )

    report = run_advisor_eval(cases=[case], include_llm=False)

    row = report["rows"][0]
    assert row["advisor"] == "deterministic"
    assert row["hypothesis_id"] == "hyp_probe_coordinate_control"
    assert row["direction_match"] is True
    assert row["boundary_awareness"] is True
    assert row["safe_patch"] is True
    assert report["summary"]["deterministic"]["rows"] == 1


def test_advisor_eval_markdown_renders_summary(tmp_path: Path) -> None:
    report_path = tmp_path / "control_compare.json"
    write_json(report_path, _control_boundary_report())
    report = run_advisor_eval(
        cases=[
            AdvisorEvalCase(
                id="control_boundary",
                report_path=report_path,
                expected_direction="probe_coordinate_control",
                expected_root_causes=("coordinate_click_surface_mismatch",),
            )
        ],
        include_llm=False,
    )

    markdown = render_advisor_eval_markdown(report)

    assert "# Advisor Evaluation" in markdown
    assert "| `deterministic` | 1 |" in markdown
    assert "`control_boundary`" in markdown


def test_advisor_eval_exposes_holdout_suite() -> None:
    cases = get_advisor_eval_cases("holdout")

    assert len(cases) == 10
    assert {case.id for case in cases} >= {
        "holdout_core_saturated",
        "holdout_challenge_efficiency_winner",
        "holdout_combined_vs_terminal_remaining_coordinate",
        "holdout_agentlab_smoke_saturated",
        "holdout_mock_advisor_quality_winner",
        "holdout_sample_retry_invalid_or_noop",
        "holdout_budget30_to_combined_remaining_coordinate",
        "holdout_hard_retry_to_full_quality_winner",
    }


def test_holdout_eval_scores_all_deterministic_cases() -> None:
    report = run_advisor_eval(case_suite="holdout")

    assert report["case_count"] == 10
    assert report["summary"]["deterministic"]["rows"] == 10
    assert {row["case_id"] for row in report["rows"]} == {
        case.id for case in get_advisor_eval_cases("holdout")
    }


def test_advisor_eval_exposes_tool_suite() -> None:
    cases = get_advisor_eval_cases("tool")

    assert [case.id for case in cases] == [
        "tool_terminal_probe_to_policy",
        "tool_compose_scroll_terminal",
        "tool_grid_probe_to_policy",
    ]


def test_tool_agent_eval_scores_tool_use_against_pretool_baseline() -> None:
    report = run_advisor_eval(
        case_suite="tool",
        include_tool_agent=True,
        include_tool_pretool=True,
    )

    assert report["case_count"] == 3
    assert report["summary"]["tool-agent"]["rows"] == 3
    assert report["summary"]["tool-agent"]["direction_match_rate"] == 1.0
    assert report["summary"]["tool-agent-pretool"]["direction_match_rate"] == 0.0
    assert report["summary"]["tool-agent"]["avg_score"] > report["summary"]["tool-agent-pretool"][
        "avg_score"
    ]


def _control_boundary_report():
    baseline = [
        RunRecord(
            experiment_id="base",
            config_id="baseline",
            task_id="browsergym/miniwob.click-pie#seed=49",
            status="success",
            normalized_score=1.0,
            step_count=2,
            latency_sec=1.0,
        )
    ]
    candidate = [
        RunRecord(
            experiment_id="new",
            config_id="variant",
            task_id="browsergym/miniwob.click-pie#seed=49",
            status="max_steps",
            normalized_score=0.0,
            step_count=20,
            latency_sec=20.0,
            failure_type="max_steps",
        )
    ]
    return build_comparison_report(baseline, candidate, taskset_id="smoke")
