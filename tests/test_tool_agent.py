from __future__ import annotations

from pathlib import Path

from baeloop.tool_agent import render_tool_agent_markdown, run_tool_optimization_agent


def test_tool_agent_uses_grid_probe_to_move_from_investigation_to_patch() -> None:
    run = run_tool_optimization_agent(
        Path("reports/agentlab_hard_combined_vs_terminal_policy_compare.json")
    )

    assert run.pre_tool_hypothesis_id == "hyp_tool_investigate_before_patch"
    assert run.final_hypothesis_id == "hyp_grid_coordinate_click"
    assert run.decision_changed_by_tools is True
    assert run.selected_root_cause == "coordinate_click_miss"
    assert [call.tool_name for call in run.tool_calls] == [
        "inspect_compare_report",
        "inspect_grid_probe",
    ]
    assert run.tool_calls[-1].observation["patch_mature"] is True
    assert run.proposal.patch["action_policy"]["policies"][-1] == "grid_coordinate_click"


def test_tool_agent_uses_terminal_probe_for_terminal_root_cause() -> None:
    run = run_tool_optimization_agent(Path("reports/agentlab_hard_scroll_policy_compare.json"))

    assert run.final_hypothesis_id == "hyp_terminal_keyboard_type"
    assert run.selected_root_cause == "terminal_input_action_mismatch"
    assert "inspect_terminal_probe" in [call.tool_name for call in run.tool_calls]
    assert run.proposal.patch["action_policy"]["name"] == "terminal_keyboard_type"


def test_tool_agent_composes_policies_when_terminal_fix_regresses_scroll() -> None:
    run = run_tool_optimization_agent(Path("reports/agentlab_hard_terminal_policy_compare.json"))

    assert run.final_hypothesis_id == "hyp_combine_scroll_and_terminal_policies"
    assert run.selected_root_cause == "compose_scroll_and_terminal"
    assert "inspect_terminal_probe" in [call.tool_name for call in run.tool_calls]
    assert "inspect_policy_replay" in [call.tool_name for call in run.tool_calls]
    assert run.proposal.patch["action_policy"]["policies"] == [
        "scroll_before_submit",
        "terminal_keyboard_type",
    ]


def test_tool_agent_uses_control_diagnostic_before_patch() -> None:
    run = run_tool_optimization_agent(Path("reports/agentlab_control_full_policy_compare.json"))

    assert run.pre_tool_hypothesis_id == "hyp_tool_investigate_before_patch"
    assert run.final_hypothesis_id == "hyp_probe_coordinate_control"
    assert run.decision_changed_by_tools is True
    assert run.selected_root_cause == "control_surface_probe"
    assert [call.tool_name for call in run.tool_calls] == [
        "inspect_compare_report",
        "inspect_control_failure_evidence",
    ]
    assert run.tool_calls[-1].observation["patch_mature"] is False
    assert run.tool_calls[-1].observation["needs_fresh_probe"] is True
    assert run.proposal.patch == {}
    assert run.proposal.intervention is not None
    assert run.proposal.intervention.kind == "investigation"


def test_tool_agent_uses_quality_diagnostic_to_hold_broad_winner() -> None:
    run = run_tool_optimization_agent(Path("reports/agentlab_broad_full_policy_compare.json"))

    assert run.pre_tool_hypothesis_id == "hyp_tool_investigate_before_patch"
    assert run.final_hypothesis_id == "hyp_keep_quality_winner"
    assert run.decision_changed_by_tools is True
    assert run.selected_root_cause == "quality_winner_hold"
    assert [call.tool_name for call in run.tool_calls] == [
        "inspect_compare_report",
        "inspect_quality_winner_evidence",
    ]
    assert run.tool_calls[-1].observation["hold_mature"] is True
    assert run.tool_calls[-1].observation["patch_mature"] is False
    assert run.proposal.patch == {}
    assert run.proposal.intervention is not None
    assert run.proposal.intervention.kind == "hold"


def test_tool_agent_markdown_renders_tool_transcript() -> None:
    run = run_tool_optimization_agent(
        Path("reports/agentlab_hard_combined_vs_terminal_policy_compare.json")
    )

    markdown = render_tool_agent_markdown(run)

    assert "# Tool-Using Optimization Agent Run" in markdown
    assert "`inspect_compare_report`" in markdown
    assert "`inspect_grid_probe`" in markdown
    assert "`hyp_grid_coordinate_click`" in markdown
